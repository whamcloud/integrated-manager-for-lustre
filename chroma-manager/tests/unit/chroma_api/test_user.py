from django.contrib.auth.models import User, Group
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestUserResource(ChromaApiTestCase):
    """Test that old_password is checked in PUTs to user, unless the superuser is
       modifying another user."""

    def test_HYD995_superuser_self(self):
        """Superuser changing his own password -- old_password required"""

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        me['password1'] = "newpwd"
        me['password2'] = "newpwd"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpBadRequest(response)

        me['old_password'] = "chr0m4_d3bug"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpAccepted(response)

    def test_HYD995_superuser_muggle(self):
        """Superuser changing normal user's password -- old_password not required"""

        muggle = User.objects.create_user("muggle", "", "muggle123")
        muggle.groups.add(Group.objects.get(name='filesystem_users'))
        muggle_data = self.deserialize(self.api_client.get("/api/user/%s/" % muggle.id))
        muggle_data['password1'] = "newpwd"
        muggle_data['password2'] = "newpwd"
        response = self.api_client.put(muggle_data['resource_uri'], data = muggle_data)
        self.assertHttpAccepted(response)

    def test_HYD995_muggle_self(self):
        """Normal user changing his own password -- old_password required"""

        muggle = User.objects.create_user("muggle", "", "muggle123")
        muggle.groups.add(Group.objects.get(name='filesystem_users'))

        # Login as the normal user
        self.api_client.client.login(username = 'muggle', password = 'muggle123')
        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertEqual(int(me['id']), int(muggle.id))

        me['password1'] = "newpwd"
        me['password2'] = "newpwd"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpBadRequest(response)

        me['old_password'] = "muggle123"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpAccepted(response)
