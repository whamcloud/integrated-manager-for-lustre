from functools import partial

from django.test import TestCase
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User

from mock import patch

from settings import SITE_ROOT
from os import path, remove

from chroma_core.lib.service_config import SupervisorStatus


credentials = {
    "username": "non_superuser",
    "password": "foo"
}

base_template = path.join(SITE_ROOT, 'chroma_ui', 'templates', 'new', 'base.html')


@patch.object(SupervisorStatus, "get_non_running_services")
class TestLoginView(TestCase):
    def setUp(self):
        self.super_user = User.objects.create(username="su", is_superuser=True)
        self.user = User.objects.create_user(**credentials)

        self.get_login_page = partial(self.client.get, "/ui/login/")

        open(base_template, 'a').close()

    def test_login_page_is_rendered(self, mock_method):
        mock_method.return_value = []
        with self.assertTemplateUsed("new/login.html"):
            self.get_login_page()

    @patch("chroma_ui.views._build_cache")
    def test_redirect_occurs_if_user_is_authenticated_and_eula_accepted(self, mock_method, _build_cache):
        mock_method.return_value = []
        _build_cache.return_value = {}

        self.super_user.get_profile().accepted_eula = True
        self.super_user.get_profile().save()

        self.client.login(**credentials)

        resp = self.get_login_page(follow=True)

        self.assertEqual(resp.redirect_chain, [("http://testserver/ui/", 302)])

    def test_logout_occurs_if_user_is_authenticated_and_eula_not_accepted(self, mock_method):
        mock_method.return_value = []

        self.client.login(**credentials)

        self.assertTrue(SESSION_KEY in self.client.session)

        self.get_login_page()

        self.assertTrue(SESSION_KEY not in self.client.session)

    def tearDown(self):
        self.user.delete()
        self.super_user.delete()

        remove(base_template)
