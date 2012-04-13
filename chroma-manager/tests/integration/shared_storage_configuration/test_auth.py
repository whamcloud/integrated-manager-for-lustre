
from testconfig import config

from tests.utils.http_requests import HttpRequests
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestAuthentication(ChromaIntegrationTestCase):
    def setUp(self):
        self.chroma_manager = HttpRequests(server_http_url =
            config['chroma_managers'][0]['server_http_url'])

    def test_login(self):
        """Test that we can authenticate with the API and get
        back session information"""
        # Usually wouldn't do this kind of unit testing of API calls from integration
        # tests, but in the case of this stuff we need to include the whole middleware
        # stack to check tokens make it through okay.

        user = config['chroma_managers'][0]['users'][0]

        # Must initially set up session and CSRF cookies
        response = self.chroma_manager.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json['user'], None)
        self.chroma_manager.session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        self.chroma_manager.session.cookies['csrftoken'] = response.cookies['csrftoken']
        self.chroma_manager.session.cookies['sessionid'] = response.cookies['sessionid']

        response = self.chroma_manager.post(
                "/api/session/",
                body = {'username': user['username'], 'password': user['password']},
        )
        self.assertEqual(response.successful, True, response.text)

        response = self.chroma_manager.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json['user']['username'], user['username'])

        response = self.chroma_manager.delete("/api/session/")
        self.assertEqual(response.successful, True, response.text)

        response = self.chroma_manager.get("/api/session/")
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(response.json['user'], None)
