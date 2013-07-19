from django.test import TestCase

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from chroma_core.models.user_profile import UserProfile


class TestUserProfile(TestCase):
    def setUp(self):
        self.super_user = User.objects.create(username="su", is_superuser=True)
        self.normal_user = User.objects.create(username="normal")

    def test_user_profile_has_eula_accepted_manager_method(self):
        self.assertEqual(UserProfile.objects.eula_accepted(), False)

    def test_user_has_user_profile(self):
        self.super_user.get_profile()
        self.normal_user.get_profile()

    def test_super_user_in_correct_state(self):
        profile = self.super_user.get_profile()

        self.assertEqual(profile.get_state(), UserProfile.EULA)

        profile.accepted_eula = True
        profile.save()

        self.assertEqual(profile.get_state(), UserProfile.PASS)

    def test_normal_user_in_correct_state(self):
        su_profile = self.super_user.get_profile()
        normal_profile = self.normal_user.get_profile()

        self.assertEqual(normal_profile.get_state(), UserProfile.DENIED)

        su_profile.accepted_eula = True
        su_profile.save()

        self.assertEqual(normal_profile.get_state(), UserProfile.PASS)

    def test_normal_user_eula_cannot_be_written(self):
        self.normal_user.get_profile().accepted_eula = True
        self.assertRaises(ValidationError, self.normal_user.get_profile().save)

    def tearDown(self):
        self.super_user.delete()
        self.normal_user.delete()
