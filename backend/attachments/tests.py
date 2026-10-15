"""FR-049 to FR-053: file and attachment management."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from taskflow.test_utils import ApiTestCase
from tasks.models import Task

from .models import Attachment, AttachmentSettings


def make_file(name='notes.txt', content=b'hello world', content_type='text/plain'):
    return SimpleUploadedFile(name, content, content_type=content_type)


class AttachmentTests(ApiTestCase):
    def make_task(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def upload(self, task, user, file=None, **kwargs):
        self.as_user(user)
        f = file if file is not None else make_file(**kwargs)
        return self.client.post(reverse('attachment-list'), {'task': task.id, 'file': f}, format='multipart')

    # ---- FR-049: authorized users upload ---------------------------------------------

    def test_project_participant_uploads_outsider_cannot(self):
        task = self.make_task()
        for user in (self.pm, self.lead, self.member, self.admin):
            res = self.upload(task, user, name=f'{user.username}.txt')
            self.assertEqual(res.status_code, 201, (user.username, res.data))
        for user in (self.outsider, self.other_pm):
            self.assertEqual(self.upload(task, user).status_code, 400, user.username)

    def test_cannot_upload_to_closed_project_task(self):
        task = self.make_task()
        self.project.status = 'CLOSED'
        self.project.save()
        self.assertEqual(self.upload(task, self.pm).status_code, 400)

    # ---- FR-051: metadata -------------------------------------------------------------

    def test_metadata_recorded(self):
        task = self.make_task()
        res = self.upload(task, self.member, name='design.pdf', content=b'%PDF-1.4', content_type='application/pdf')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data['filename'], res.data['uploaded_by'], res.data['content_type']),
                          ('design.pdf', self.member.id, 'application/pdf'))
        self.assertGreater(res.data['size_bytes'], 0)
        self.assertNotIn('file', res.data)  # raw file field is write-only; download is via the action

    # ---- FR-052: size / type restrictions ---------------------------------------------

    def test_disallowed_extension_rejected(self):
        task = self.make_task()
        res = self.upload(task, self.pm, name='virus.exe')
        self.assertEqual(res.status_code, 400)
        self.assertIn('not allowed', str(res.data))

    def test_oversized_file_rejected(self):
        task = self.make_task()
        AttachmentSettings.objects.update_or_create(pk=1, defaults={'max_size_mb': 1})
        big = make_file(content=b'x' * (2 * 1024 * 1024))
        res = self.upload(task, self.pm, file=big)
        self.assertEqual(res.status_code, 400)
        self.assertIn('1MB limit', str(res.data))

    def test_admin_reconfigures_limits_others_cannot(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('attachment-settings')).status_code, 200)
        denied = self.client.patch(reverse('attachment-settings'), {'max_size_mb': 5})
        self.assertEqual(denied.status_code, 403)
        self.as_user(self.admin)
        res = self.client.patch(reverse('attachment-settings'), {'max_size_mb': 5, 'allowed_extensions': 'txt,pdf'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data['max_size_mb'], res.data['extension_list']), (5, ['txt', 'pdf']))

        task = self.make_task()
        self.assertEqual(self.upload(task, self.pm, name='sheet.xlsx').status_code, 400)  # no longer allowed
        self.assertEqual(self.upload(task, self.pm, name='ok.pdf', content_type='application/pdf').status_code, 201)

    # ---- FR-050: download is authorized ------------------------------------------------

    def test_download_requires_visibility(self):
        task = self.make_task()
        res = self.upload(task, self.pm, name='doc.txt', content=b'top secret contents')
        aid = res.data['id']
        self.as_user(self.member)
        ok = self.client.get(reverse('attachment-download', args=[aid]))
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(b''.join(ok.streaming_content), b'top secret contents')
        self.assertIn('doc.txt', ok['Content-Disposition'])

        self.as_user(self.outsider)
        self.assertEqual(self.client.get(reverse('attachment-detail', args=[aid])).status_code, 404)
        self.assertEqual(self.client.get(reverse('attachment-download', args=[aid])).status_code, 404)

    # ---- FR-053: remove -----------------------------------------------------------------

    def test_uploader_removes_own_file(self):
        task = self.make_task()
        res = self.upload(task, self.member, name='mine.txt')
        aid = res.data['id']
        self.assertEqual(self.client.delete(reverse('attachment-detail', args=[aid])).status_code, 204)
        self.assertFalse(Attachment.objects.filter(pk=aid).exists())

    def test_only_uploader_manager_or_admin_can_remove(self):
        task = self.make_task()
        res = self.upload(task, self.member, name='mine.txt')
        aid = res.data['id']
        self.as_user(self.member2)
        self.assertEqual(self.client.delete(reverse('attachment-detail', args=[aid])).status_code, 403)
        self.as_user(self.pm)
        self.assertEqual(self.client.delete(reverse('attachment-detail', args=[aid])).status_code, 204)

    def test_removal_deletes_the_underlying_file(self):
        task = self.make_task()
        res = self.upload(task, self.pm, name='temp.txt')
        aid = res.data['id']
        row = Attachment.objects.get(pk=aid)
        storage, name = row.file.storage, row.file.name
        self.assertTrue(storage.exists(name))
        self.client.delete(reverse('attachment-detail', args=[aid]))
        self.assertFalse(storage.exists(name))

    def test_attachment_metadata_does_not_leak_contact_info(self):
        task = self.make_task()
        res = self.upload(task, self.member, name='x.txt')
        self.as_user(self.member2)
        detail = self.client.get(reverse('attachment-list'), {'task': task.id}).data['results'][0]['uploaded_by_detail']
        self.assertEqual(set(detail), {'id', 'username', 'first_name', 'last_name', 'role'})
