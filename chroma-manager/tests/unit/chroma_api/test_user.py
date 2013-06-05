from django.contrib.auth.models import User, Group
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestUserResource(ChromaApiTestCase):
    """Test that old_password is checked in PUTs to user, unless the superuser is
       modifying another user."""

    def test_HYD995_superuser_self(self):
        """Superuser changing his own password -- old_password required"""

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        me['new_password1'] = "newpwd"
        me['new_password2'] = "newpwd"
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
        muggle_data['new_password1'] = "newpwd"
        muggle_data['new_password2'] = "newpwd"
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

        me['new_password1'] = "newpwd"
        me['new_password2'] = "newpwd"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpBadRequest(response)

        me['old_password'] = "muggle123"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpAccepted(response)

    def test_user_details_update(self):
        """Users should be able to update their details (first/last, email)"""
        username = "joebob"
        password = "nancysue"

        joebob = User.objects.create_user(username, "", password)
        joebob.groups.add(Group.objects.get(name='filesystem_users'))

        # Log in
        self.api_client.client.login(username = username, password = password)

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertEqual(int(me['id']), int(joebob.id))
        self.assertEqual(me['email'], "")

        me['first_name'] = "Joebob"
        me['last_name'] = "Josephson"
        me['email'] = "joebob@joebob.rocks"
        response = self.api_client.put("/api/user/%s/" % me['id'], data = me)
        self.assertHttpAccepted(response)

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertEqual(int(me['id']), int(joebob.id))
        self.assertEqual(me['email'], "joebob@joebob.rocks")
        self.assertEqual(me['full_name'], "Joebob Josephson")

    def test_superuser_accepted_eula(self):
        superuser = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertFalse(superuser['accepted_eula'])

        superuser['accepted_eula'] = True

        response = self.api_client.put("/api/user/%s/" % superuser["id"], data=superuser)
        self.assertHttpAccepted(response)

        superuser = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertTrue(superuser['accepted_eula'])

    def test_non_superuser_can_see_accept_eula(self):
        credentials = {
            "username": "non_superuser",
            "password": "foo"
        }

        non_superuser = User.objects.create_user(**credentials)
        non_superuser.groups.add(Group.objects.get(name='filesystem_users'))

        self.api_client.client.login(**credentials)

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertFalse(me["accepted_eula"])

        superuser = User.objects.create_superuser("superuser", "", "bar")
        superuser.userprofile.accepted_eula = True
        superuser.userprofile.save()

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertTrue(me["accepted_eula"])

    def test_is_superuser_is_readonly(self):
        superuser = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertTrue(superuser["is_superuser"])
        superuser["is_superuser"] = False

        response = self.api_client.put("/api/user/%s/" % superuser["id"], data=superuser)
        self.assertHttpAccepted(response)

        superuser = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertTrue(superuser['is_superuser'])

    def test_accept_eula_is_readonly_for_non_superuser(self):
        data = {
            "email": "test@test.com",
            "first_name": "",
            "groups": ["/api/group/3/"],
            "last_name": "",
            "password1": "a",
            "password2": "a",
            "username": "test",
            "accepted_eula": True
        }

        resp = self.api_client.post("/api/user/", data=data)
        self.assertHttpCreated(resp)

        self.api_client.client.login(username=data["username"], password=data["password1"])

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertFalse(me["accepted_eula"])
        self.assertFalse(me["is_superuser"])

        me["accepted_eula"] = True

        resp = self.api_client.put("/api/user/%s/" % me["id"], data=me)
        self.assertHttpAccepted(resp)

        me = self.deserialize(self.api_client.get("/api/session/"))['user']
        self.assertFalse(me["accepted_eula"])
