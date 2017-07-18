# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.utils import timezone
import json


class UserProfileManager(models.Manager):
    def eula_accepted(self):
        return self.filter(user__is_superuser=True, accepted_eula=True).exists()


class UserProfile(models.Model):
    class Meta:
        app_label = 'chroma_core'

    PASS = "pass"
    EULA = "eula"
    DENIED = "denied"
    STATES = (PASS, EULA, DENIED)

    # This field is required.
    user = models.OneToOneField(User)

    objects = UserProfileManager()

    accepted_eula = models.BooleanField(default=False)

    _gui_config = models.TextField(db_column='gui_config', default='{}')
    modified_at = models.DateTimeField(default=timezone.now, blank=True, editable=False)

    @property
    def gui_config(self):
        return json.loads(self._gui_config)

    @gui_config.setter
    def gui_config(self, config):
        self._gui_config = json.dumps(config)

    def clean(self):
        from django.core.exceptions import ValidationError
        # Don't allow accept_eula to be set for non-superusers.
        if not self.user.is_superuser and self.accepted_eula:
            raise ValidationError("Eula cannot be set for non-superuser.")

    def get_state(self):
        eula_accepted = self._default_manager.eula_accepted()

        if eula_accepted:
            return self.PASS
        else:
            return self.EULA if self.user.is_superuser else self.DENIED

    def save(self, *args, **kwargs):
        self.full_clean()
        super(UserProfile, self).save(*args, **kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User, dispatch_uid="create_user_profile_post_save")
