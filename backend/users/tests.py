from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Role, User

PASSWORD = 'Sup3r-secret-pw'


def make_user(username, role=Role.TEAM_MEMBER, **extra):
    return User.objects.create_user(
        username=username, password=PASSWORD, role=role,
        email=f'{username}@example.com', first_name=username.title(), last_name='Test', **extra,
    )


class AuthTests(APITestCase):
    def login(self, username, password=PASSWORD):
        return self.client.post(reverse('login'), {'username': username, 'password': password})

    def auth_as(self, user):
        res = self.login(user.username)
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    # FR-001
    def test_register_creates_team_member(self):
        res = self.client.post(reverse('register'), {
            'username': 'newbie', 'email': 'newbie@example.com',
            'first_name': 'New', 'last_name': 'Bie', 'password': PASSWORD,
        })
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(User.objects.get(username='newbie').role, Role.TEAM_MEMBER)

    def test_register_cannot_choose_admin_role(self):
        res = self.client.post(reverse('register'), {
            'username': 'sneaky', 'email': 's@example.com', 'first_name': 'S',
            'last_name': 'S', 'password': PASSWORD, 'role': 'ADMIN',
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get(username='sneaky').role, Role.TEAM_MEMBER)

    def test_register_rejects_weak_password_and_duplicate_email(self):
        base = {'username': 'a1', 'email': 'a1@example.com', 'first_name': 'A', 'last_name': 'B'}
        self.assertEqual(self.client.post(reverse('register'), {**base, 'password': '123'}).status_code, 400)
        make_user('taken')
        dup = {**base, 'username': 'a2', 'email': 'TAKEN@example.com', 'password': PASSWORD}
        self.assertEqual(self.client.post(reverse('register'), dup).status_code, 400)

    # FR-002
    def test_login_and_logout_revokes_refresh_token(self):
        make_user('alice')
        tokens = self.auth_as(User.objects.get(username='alice'))
        self.assertEqual(self.client.post(reverse('logout'), {'refresh': tokens['refresh']}).status_code, 205)
        res = self.client.post(reverse('token_refresh'), {'refresh': tokens['refresh']})
        self.assertEqual(res.status_code, 401)

    def test_login_wrong_password(self):
        make_user('alice')
        self.assertEqual(self.login('alice', 'nope').status_code, 400)

    # FR-003
    def test_update_own_profile_but_not_role(self):
        alice = make_user('alice')
        self.auth_as(alice)
        res = self.client.patch(reverse('user-me'), {'first_name': 'Alicia', 'job_title': 'Dev', 'role': 'ADMIN'})
        self.assertEqual(res.status_code, 200, res.data)
        alice.refresh_from_db()
        self.assertEqual((alice.first_name, alice.job_title), ('Alicia', 'Dev'))
        self.assertEqual(alice.role, Role.TEAM_MEMBER)

    def test_change_password_requires_current_password(self):
        alice = make_user('alice')
        self.auth_as(alice)
        url = reverse('user-change-password')
        bad = self.client.post(url, {'current_password': 'wrong', 'new_password': 'An0ther-good-pw'})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(url, {'current_password': PASSWORD, 'new_password': 'An0ther-good-pw'})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.login('alice', 'An0ther-good-pw').status_code, 200)

    # FR-004 / FR-006
    def test_non_admin_cannot_manage_users(self):
        alice = make_user('alice')
        bob = make_user('bob')
        self.auth_as(alice)
        self.assertEqual(self.client.post(reverse('user-deactivate', args=[bob.pk])).status_code, 403)
        self.assertEqual(self.client.patch(reverse('user-detail', args=[bob.pk]), {'role': 'ADMIN'}).status_code, 403)

    def test_non_admin_gets_minimal_directory_of_active_users_only(self):
        alice = make_user('alice')
        bob = make_user('bob')
        gone = make_user('gone')
        gone.is_active_member = False
        gone.save()
        self.auth_as(alice)
        res = self.client.get(reverse('user-list'))
        self.assertEqual(res.status_code, 200)
        names = {u['username'] for u in res.data['results']}
        self.assertEqual(names, {'alice', 'bob'})  # deactivated user hidden
        for entry in res.data['results']:
            self.assertEqual(set(entry), {'id', 'username', 'first_name', 'last_name', 'role'})
        self.assertEqual(self.client.get(reverse('user-detail', args=[gone.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('user-detail', args=[bob.pk])).status_code, 200)

    def test_admin_sees_full_records_including_deactivated(self):
        admin = make_user('boss', Role.ADMIN)
        gone = make_user('gone')
        gone.is_active_member = False
        gone.save()
        self.auth_as(admin)
        res = self.client.get(reverse('user-list'))
        by_name = {u['username']: u for u in res.data['results']}
        self.assertIn('gone', by_name)
        self.assertIn('email', by_name['gone'])
        self.assertFalse(by_name['gone']['is_active_member'])

    def test_anonymous_cannot_list_users(self):
        self.assertEqual(self.client.get(reverse('user-list')).status_code, 401)

    def test_admin_creates_user_with_role(self):
        admin = make_user('boss', Role.ADMIN)
        self.auth_as(admin)
        res = self.client.post(reverse('user-list'), {
            'username': 'lead1', 'email': 'lead1@example.com', 'first_name': 'Lee',
            'last_name': 'Der', 'password': PASSWORD, 'role': 'TEAM_LEADER',
        })
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(User.objects.get(username='lead1').role, Role.TEAM_LEADER)

    def test_deactivate_blocks_login_and_existing_tokens_then_reactivate(self):
        admin = make_user('boss', Role.ADMIN)
        bob = make_user('bob')
        bob_tokens = self.auth_as(bob)
        self.client.credentials()
        self.auth_as(admin)
        self.assertEqual(self.client.post(reverse('user-deactivate', args=[bob.pk])).status_code, 200)

        self.client.credentials()
        self.assertEqual(self.login('bob').status_code, 400)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {bob_tokens['access']}")
        self.assertEqual(self.client.get(reverse('user-me')).status_code, 401)
        self.assertEqual(
            self.client.post(reverse('token_refresh'), {'refresh': bob_tokens['refresh']}).status_code, 401
        )

        self.client.credentials()
        self.auth_as(admin)
        self.assertEqual(self.client.post(reverse('user-reactivate', args=[bob.pk])).status_code, 200)
        self.client.credentials()
        self.assertEqual(self.login('bob').status_code, 200)

    def test_admin_cannot_deactivate_or_demote_self(self):
        admin = make_user('boss', Role.ADMIN)
        self.auth_as(admin)
        self.assertEqual(self.client.post(reverse('user-deactivate', args=[admin.pk])).status_code, 400)
        res = self.client.patch(reverse('user-detail', args=[admin.pk]), {'role': 'TEAM_MEMBER'})
        self.assertEqual(res.status_code, 400)

    def test_admin_changes_role(self):
        admin = make_user('boss', Role.ADMIN)
        bob = make_user('bob')
        self.auth_as(admin)
        res = self.client.patch(reverse('user-detail', args=[bob.pk]), {'role': 'PROJECT_MANAGER'})
        self.assertEqual(res.status_code, 200, res.data)
        bob.refresh_from_db()
        self.assertEqual(bob.role, Role.PROJECT_MANAGER)

    # FR-007
    def test_admin_reset_password_generates_temp_and_ends_sessions(self):
        admin = make_user('boss', Role.ADMIN)
        bob = make_user('bob')
        bob_tokens = self.auth_as(bob)
        self.client.credentials()
        self.auth_as(admin)
        res = self.client.post(reverse('user-reset-password', args=[bob.pk]), {})
        self.assertEqual(res.status_code, 200, res.data)
        temp = res.data['temporary_password']

        self.client.credentials()
        self.assertEqual(self.login('bob').status_code, 400)  # old password dead
        self.assertEqual(self.login('bob', temp).status_code, 200)
        res = self.client.post(reverse('token_refresh'), {'refresh': bob_tokens['refresh']})
        self.assertEqual(res.status_code, 401)  # old session revoked

    # role assignment for superusers
    def test_createsuperuser_gets_admin_role(self):
        su = User.objects.create_superuser('root', 'root@example.com', PASSWORD)
        self.assertEqual(su.role, Role.ADMIN)
