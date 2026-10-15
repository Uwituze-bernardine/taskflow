from rest_framework.test import APITestCase

from projects.models import Project, ProjectMembership
from users.models import Role, User

PASSWORD = 'Sup3r-secret-pw'


def make_user(username, role=Role.TEAM_MEMBER, **extra):
    return User.objects.create_user(
        username=username, password=PASSWORD, role=role, email=f'{username}@example.com',
        first_name=username.title(), last_name='Test', **extra,
    )


class ApiTestCase(APITestCase):
    """Cast: admin, a project manager who runs `project`, its team leader + member, and an outsider."""

    def setUp(self):
        self.admin = make_user('admin', Role.ADMIN)
        self.pm = make_user('pm', Role.PROJECT_MANAGER)
        self.other_pm = make_user('otherpm', Role.PROJECT_MANAGER)
        self.lead = make_user('lead', Role.TEAM_LEADER)
        self.member = make_user('member')
        self.member2 = make_user('member2')
        self.outsider = make_user('outsider')
        self.project = Project.objects.create(name='Apollo', manager=self.pm, created_by=self.pm, status='ACTIVE')
        for u in (self.lead, self.member, self.member2):
            ProjectMembership.objects.create(project=self.project, user=u)

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return user

    def ids(self, response):
        return {row['id'] for row in response.data['results']}
