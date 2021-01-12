import datetime

from chroma_core.models.registration_token import RegistrationToken, SECRET_LENGTH
from django.contrib.auth.models import User, Group

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_api.tastypie_test import TestApiClient
from emf_common.lib.date_time import EMFDateTime


class TestRegistrationTokenResource(ChromaApiTestCase):
    RESOURCE_PATH = "/api/registration_token/"

    def setUp(self):
        super(TestRegistrationTokenResource, self).setUp()

        # Grab a profile to use for creation tokens, doesn't matter what it is
        response = self.api_client.get("/api/server_profile/")
        self.profile = self.deserialize(response)["objects"][0]

    def test_cancel_token(self):
        """Test that we can cancel at token using PATCH"""
        response = self.api_client.post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
        self.assertHttpCreated(response)
        token_uri = self.deserialize(response)["resource_uri"]
        response = self.api_client.patch(token_uri, data={"cancelled": True})
        self.assertHttpAccepted(response)

        # Now that its cancelled, it should no longer be visible in the API
        response = self.api_client.get(token_uri)
        self.assertHttpNotFound(response)
        response = self.api_client.get(self.RESOURCE_PATH)
        self.assertEqual(len(self.deserialize(response)["objects"]), 0)

        # Check that we modified one instead of creating a new one
        self.assertEqual(RegistrationToken.objects.count(), 1)

    def test_readonly_attributes(self):
        """Test that attributes which should be readonly reject PATCHes"""
        response = self.api_client.post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
        self.assertHttpCreated(response)
        original_object = self.deserialize(response)
        token_uri = original_object["resource_uri"]

        readonly_test_values = {"secret": "X" * SECRET_LENGTH * 2, "expiry": EMFDateTime.utcnow(), "credits": 666}

        for attribute, test_val in readonly_test_values.items():
            response = self.api_client.patch(token_uri, data={attribute: test_val})
            self.assertHttpBadRequest(response)
            # Check it hasn't changed
            self.assertDictEqual(self.deserialize(self.api_client.get(token_uri)), original_object)

    def test_creation(self):
        """
        During a POST, only expiry should be settable
        """

        # Empty is OK
        response = self.api_client.post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
        self.assertHttpCreated(response)

        expiry_value = EMFDateTime.utcnow()
        expiry_value += datetime.timedelta(seconds=120)
        expiry_value = expiry_value.replace(microsecond=0)

        creation_allowed_values = {"expiry": expiry_value.isoformat(), "credits": 129}

        for attr, test_val in creation_allowed_values.items():
            response = self.api_client.post(
                self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"], attr: test_val}
            )
            self.assertHttpCreated(response)
            created_obj = self.deserialize(response)
            self.assertEqual(created_obj[attr], test_val)

        # Anything else is not OK
        creation_forbidden_values = {"secret": "X" * SECRET_LENGTH * 2, "cancelled": True, "id": 0}
        for attribute, test_val in creation_forbidden_values.items():
            response = self.api_client.post(
                self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"], attribute: test_val}
            )
            self.assertHttpBadRequest(response)


class TestTokenAuthorization(ChromaApiTestCase):
    RESOURCE_PATH = "/api/registration_token/"

    def setUp(self):
        super(TestTokenAuthorization, self).setUp()

        users = [
            {"username": "token_user", "password": "user123", "group": "filesystem_users"},
            {"username": "token_admin", "password": "admin123", "group": "filesystem_administrators"},
            {"username": "token_superuser", "password": "superuser123", "group": "superusers"},
        ]

        self.clients = {}
        for user in users:
            if user["group"] == "superusers":
                obj = User.objects.create_superuser(user["username"], "", user["password"])
            else:
                obj = User.objects.create_user(user["username"], "", user["password"])
            obj.groups.add(Group.objects.get(name=user["group"]))
            self.clients[user["username"]] = TestApiClient()
            self.clients[user["username"]].client.login(username=user["username"], password=user["password"])

        # Grab a profile to use for creation tokens, doesn't matter what it is
        response = self.api_client.get("/api/server_profile/")
        self.profile = self.deserialize(response)["objects"][0]

    def test_post(self):
        """Test that only filesystem_admins or superusers can create a token"""

        users = {"token_user": False, "token_superuser": True, "token_admin": True}
        for username, should_succeed in users.items():
            response = self.clients[username].post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
            if should_succeed:
                self.assertHttpCreated(response)
            else:
                self.assertHttpUnauthorized(response)

    def test_get(self):
        """Test that tokens are not visible to normal users"""

        response = self.api_client.post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
        self.assertHttpCreated(response)
        token_uri = self.deserialize(response)["resource_uri"]

        expected_rows = {"token_user": 0, "token_superuser": 1, "token_admin": 1}

        for username, row_count in expected_rows.items():
            # Try a list GET
            response = self.clients[username].get(self.RESOURCE_PATH)
            self.assertHttpOK(response)
            self.assertEqual(len(self.deserialize(response)["objects"]), row_count)

            # Try a detail GET
            response = self.clients[username].get(token_uri)
            if row_count:
                self.assertHttpOK(response)
            else:
                self.assertHttpUnauthorized(response)

    def test_patch(self):
        """Test that normal users cannot patch"""
        users_allowed = {"token_user": False, "token_superuser": True, "token_admin": True}

        for username, allowed in users_allowed.items():
            # Create using the default test client, before trying each
            # of the specific user clients for PATCHing
            response = self.api_client.post(self.RESOURCE_PATH, data={"profile": self.profile["resource_uri"]})
            self.assertHttpCreated(response)
            token_uri = self.deserialize(response)["resource_uri"]

            patch_response = self.clients[username].patch(token_uri, data={"cancelled": True})
            if allowed:
                self.assertHttpAccepted(patch_response)
            else:
                self.assertHttpUnauthorized(patch_response)
