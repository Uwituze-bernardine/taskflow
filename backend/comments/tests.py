"""FR-043 to FR-048: comments and collaboration."""
from django.urls import reverse

from notifications.models import Notification
from taskflow.test_utils import ApiTestCase
from tasks.models import Task

from .models import Comment


class CommentTests(ApiTestCase):
    def make_task(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def post(self, task, body, user=None):
        if user:
            self.as_user(user)
        return self.client.post(reverse('comment-list'), {'task': task.id, 'body': body}, format='json')

    # ---- FR-043: authorized users comment ------------------------------------------

    def test_project_participant_comments_outsider_cannot(self):
        task = self.make_task()
        for user in (self.pm, self.lead, self.member, self.admin):
            res = self.post(task, f'hello from {user.username}', user)
            self.assertEqual(res.status_code, 201, (user.username, res.data))
        for user in (self.outsider, self.other_pm):
            res = self.post(task, 'nope', user)
            self.assertEqual(res.status_code, 400, user.username)  # task not in their visible queryset

    def test_cannot_comment_on_closed_project_task(self):
        task = self.make_task()
        self.project.status = 'CLOSED'
        self.project.save()
        self.assertEqual(self.post(task, 'too late', self.pm).status_code, 400)

    def test_empty_comment_rejected(self):
        task = self.make_task()
        self.assertEqual(self.post(task, '   ', self.pm).status_code, 400)

    # ---- FR-044: chronological order ------------------------------------------------

    def test_comments_are_chronological(self):
        task = self.make_task()
        self.as_user(self.pm)
        for body in ('first', 'second', 'third'):
            self.post(task, body)
        res = self.client.get(reverse('comment-list'), {'task': task.id})
        self.assertEqual([c['body'] for c in res.data['results']], ['first', 'second', 'third'])

    # ---- FR-045/046: mentions --------------------------------------------------------

    def test_mentioning_a_participant_notifies_them(self):
        task = self.make_task(assigned_to=self.member)
        res = self.post(task, f'hey @{self.lead.username} and @{self.member.username}, look at this', self.pm)
        self.assertEqual(res.status_code, 201, res.data)
        names = {u['username'] for u in res.data['mentioned_users_detail']}
        self.assertEqual(names, {self.lead.username, self.member.username})
        self.assertTrue(Notification.objects.filter(recipient=self.lead, task=task).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member, task=task).exists())

    def test_mentioning_someone_who_cannot_see_the_task_is_ignored(self):
        task = self.make_task()
        res = self.post(task, f'cc @{self.outsider.username}', self.pm)
        self.assertEqual(res.data['mentioned_users_detail'], [])
        self.assertFalse(Notification.objects.filter(recipient=self.outsider, task=task).exists())

    def test_self_mention_does_not_notify(self):
        task = self.make_task()
        self.post(task, f'note to self @{self.pm.username}', self.pm)
        self.assertFalse(Notification.objects.filter(recipient=self.pm, task=task).exists())

    def test_admin_can_always_be_mentioned(self):
        task = self.make_task()  # admin is not a project participant, but can see everything
        res = self.post(task, f'ping @{self.admin.username}', self.pm)
        self.assertEqual([u['username'] for u in res.data['mentioned_users_detail']], [self.admin.username])

    def test_editing_a_comment_recomputes_mentions_and_only_notifies_new_ones(self):
        task = self.make_task()
        res = self.post(task, f'hi @{self.lead.username}', self.pm)
        cid = res.data['id']
        Notification.objects.all().delete()
        self.as_user(self.pm)
        res = self.client.patch(reverse('comment-detail', args=[cid]), {'body': f'hi @{self.lead.username} and @{self.member.username}'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertFalse(Notification.objects.filter(recipient=self.lead).exists())  # already mentioned before
        self.assertTrue(Notification.objects.filter(recipient=self.member).exists())  # newly mentioned

    # ---- FR-048: edit / delete own, subject to permissions --------------------------

    def test_author_edits_own_comment_marks_edited(self):
        task = self.make_task()
        res = self.post(task, 'v1', self.pm)
        cid = res.data['id']
        res = self.client.patch(reverse('comment-detail', args=[cid]), {'body': 'v2'})
        self.assertEqual((res.status_code, res.data['body'], res.data['is_edited']), (200, 'v2', True))

    def test_only_author_can_edit(self):
        task = self.make_task()
        res = self.post(task, 'mine', self.pm)
        cid = res.data['id']
        self.as_user(self.lead)
        self.assertEqual(self.client.patch(reverse('comment-detail', args=[cid]), {'body': 'hijack'}).status_code, 403)

    def test_author_deletes_own_comment_soft_delete_preserves_history(self):
        task = self.make_task()
        res = self.post(task, 'to remove', self.pm)
        cid = res.data['id']
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[cid])).status_code, 204)
        row = Comment.objects.get(pk=cid)
        self.assertTrue(row.is_deleted)
        self.assertEqual(row.body, 'to remove')  # FR-047: the row survives, content just hidden via the API
        self.as_user(self.lead)
        listed = self.client.get(reverse('comment-list'), {'task': task.id}).data['results']
        self.assertEqual(len(listed), 1)  # still present in the discussion
        self.assertEqual((listed[0]['is_deleted'], listed[0]['body']), (True, 'This comment was deleted.'))

    def test_task_manager_and_admin_can_moderate_others_comments(self):
        task = self.make_task()
        res = self.post(task, 'by member', self.member)
        cid1 = res.data['id']
        self.as_user(self.pm)  # manages the project the task is in
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[cid1])).status_code, 204)

        res = self.post(task, 'again', self.member)
        cid2 = res.data['id']
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[cid2])).status_code, 204)

    def test_uninvolved_member_cannot_delete_someone_elses_comment(self):
        task = self.make_task()
        res = self.post(task, 'by lead', self.lead)
        cid = res.data['id']
        self.as_user(self.member2)  # a project member, but not a manager and not the author
        self.assertEqual(self.client.delete(reverse('comment-detail', args=[cid])).status_code, 403)

    def test_cannot_edit_deleted_comment(self):
        task = self.make_task()
        res = self.post(task, 'gone soon', self.pm)
        cid = res.data['id']
        self.client.delete(reverse('comment-detail', args=[cid]))
        res = self.client.patch(reverse('comment-detail', args=[cid]), {'body': 'resurrect'})
        self.assertEqual(res.status_code, 403)

    # ---- visibility / leakage ---------------------------------------------------------

    def test_comments_hidden_from_people_who_cannot_see_the_task(self):
        task = self.make_task()
        self.post(task, 'secret-ish', self.pm)
        self.as_user(self.outsider)
        self.assertEqual(self.client.get(reverse('comment-list'), {'task': task.id}).data['results'], [])

    def test_author_details_do_not_leak_contact_info(self):
        task = self.make_task()
        res = self.post(task, 'hi', self.member)
        self.assertEqual(set(res.data['author_detail']), {'id', 'username', 'first_name', 'last_name', 'role'})
