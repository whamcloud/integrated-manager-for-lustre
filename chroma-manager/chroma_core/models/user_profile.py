#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save


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
