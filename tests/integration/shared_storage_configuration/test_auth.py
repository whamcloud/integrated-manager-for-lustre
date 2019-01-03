from testconfig import config
from tests.utils.http_requests import HttpRequests, AuthorizedHttpRequests
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestAuthentication(ChromaIntegrationTestCase):
    def setUp(self):
        super(TestAuthentication, self).setUp()

        superuser = config["chroma_managers"][0]["users"][0]
        self.reset_accounts(
            AuthorizedHttpRequests(
                superuser["username"],
                superuser["password"],
                server_http_url=config["chroma_managers"][0]["server_http_url"],
            )
        )

    def test_login(self):
        """Test that we can authenticate with the API and get
        back session information"""
        # Usually wouldn't do this kind of unit testing of API calls from integration
        # tests, but in the case of this stuff we need to include the whole middleware
        # stack to check tokens make it through okay.

        user = config["chroma_managers"][0]["users"][0]

        requests = HttpRequests(server_http_url=config["chroma_managers"][0]["server_http_url"])

        # Must initially set up session and CSRF cookies
        response = requests.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json["user"], None)
        requests.session.headers["X-CSRFToken"] = response.cookies["csrftoken"]
        requests.session.cookies["csrftoken"] = response.cookies["csrftoken"]
        requests.session.cookies["sessionid"] = response.cookies["sessionid"]

        response = requests.post("/api/session/", body={"username": user["username"], "password": user["password"]})
        self.assertEqual(response.successful, True, response.text)

        response = requests.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json["user"]["username"], user["username"])

        response = requests.delete("/api/session/")
        self.assertEqual(response.successful, True, response.text)

        response = requests.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json["user"], None)

    def test_user_management(self):
        superuser = config["chroma_managers"][0]["users"][0]
        superuser_requests = AuthorizedHttpRequests(
            superuser["username"],
            superuser["password"],
            server_http_url=config["chroma_managers"][0]["server_http_url"],
        )

        response = superuser_requests.get("/api/group/", data={"limit": 0})
        self.assertEqual(response.status_code, 200)
        groups = response.json["objects"]
        filesystem_users = None
        for group in groups:
            if group["name"] == "filesystem_users":
                filesystem_users = group
        self.assertNotEqual(filesystem_users, None)

        basic_user = {
            "groups": ["/api/group/%s/" % filesystem_users["id"]],
            "username": "jane",
            "first_name": "",
            "last_name": "",
            "email": "",
            "password1": "foo",
            "password2": "foo",
        }
        response = superuser_requests.post("/api/user/", basic_user)
        self.assertEqual(response.status_code, 201, "request %s response %s" % (basic_user, response.content))
        user = response.json
        self.assertEqual(user["password1"], None)
        self.assertEqual(user["password2"], None)

        basic_user_requests = AuthorizedHttpRequests(
            basic_user["username"],
            basic_user["password1"],
            server_http_url=config["chroma_managers"][0]["server_http_url"],
        )

        # Check that the unprivileged user can only see his own account
        response = basic_user_requests.get("/api/user/", data={"limit": 0})
        self.assertEqual(response.status_code, 200)
        users = response.json["objects"]
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["id"], user["id"])

        # Check that the unprivileged user can log himself out
        response = basic_user_requests.delete("/api/session/")
        self.assertEqual(response.status_code, 204)

        # Check that once logged out I see no users (assume settings.ALLOW_ANONYMOUS_READ=True)
        response = basic_user_requests.get("/api/user/")
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json["objects"], [])

        # Log back in
        basic_user_requests = AuthorizedHttpRequests(
            basic_user["username"],
            basic_user["password1"],
            server_http_url=config["chroma_managers"][0]["server_http_url"],
        )

        # Change my password
        user["password1"] = "bar"
        user["password2"] = "bar"
        user["old_password"] = "foo"
        response = basic_user_requests.put(user["resource_uri"], user)
        self.assertEqual(response.status_code, 200, response.content)

        # Log back in with my new password
        basic_user_requests = AuthorizedHttpRequests(
            basic_user["username"], user["password1"], server_http_url=config["chroma_managers"][0]["server_http_url"]
        )

        # Check that the unprivileged user cannot delete himself
        response = basic_user_requests.delete(user["resource_uri"])
        self.assertEqual(response.status_code, 400)

        # Check that the privileged user can delete the unprivileged user
        response = superuser_requests.delete(user["resource_uri"])
        self.assertEqual(response.status_code, 204)
