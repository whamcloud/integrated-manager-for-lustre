# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import django.contrib.auth.models
from django.contrib.contenttypes.models import ContentType
import django.contrib.auth as auth

import chroma_core.models

import settings


def setup_groups(sender, **kwargs):
    if sender.name != "chroma_core":
        return

    if auth.models.Group.objects.count() == 0:
        print("Creating groups...")
        auth.models.Group.objects.create(name="superusers")
        fsadmin_group = auth.models.Group.objects.create(name="filesystem_administrators")

        def grant_write(group, model):
            for perm in auth.models.Permission.objects.filter(content_type=ContentType.objects.get_for_model(model)):
                group.permissions.add(perm)

        def all_subclasses(cls):
            for subclass in cls.__subclasses__():
                yield subclass
                for subclass in all_subclasses(subclass):
                    yield subclass

        grant_write(fsadmin_group, chroma_core.models.ManagedTarget)
        grant_write(fsadmin_group, chroma_core.models.ManagedHost)
        grant_write(fsadmin_group, chroma_core.models.ManagedFilesystem)
        grant_write(fsadmin_group, chroma_core.models.StorageResourceRecord)
        grant_write(fsadmin_group, chroma_core.models.Job)
        grant_write(fsadmin_group, chroma_core.models.Command)
        grant_write(fsadmin_group, chroma_core.models.Volume)
        grant_write(fsadmin_group, chroma_core.models.VolumeNode)
        grant_write(fsadmin_group, django.contrib.auth.models.User)
        grant_write(fsadmin_group, chroma_core.models.RegistrationToken)

        # Allow fs admins to dismiss alerts
        grant_write(fsadmin_group, chroma_core.models.AlertState)
        for alert_klass in all_subclasses(chroma_core.models.AlertStateBase):
            grant_write(fsadmin_group, alert_klass)

        fsusers_group = auth.models.Group.objects.create(name="filesystem_users")
        # For modifying his own account
        grant_write(fsusers_group, django.contrib.auth.models.User)

    if settings.DEBUG and auth.models.User.objects.count() == 0:
        print("***\n" * 3),
        print("*** SECURITY WARNING: You are running in DEBUG mode and default users have been created")
        print("***\n" * 3)
        user = auth.models.User.objects.create_superuser("admin", "admin@debug.co.eh", "lustre")
        user.groups.add(auth.models.Group.objects.get(name="superusers"))
        user = auth.models.User.objects.create_user("debug", "debug@debug.co.eh", "lustre")
        user.groups.add(auth.models.Group.objects.get(name="filesystem_administrators"))
        user = auth.models.User.objects.create_user("user", "user@debug.co.eh", "lustre")
        user.groups.add(auth.models.Group.objects.get(name="filesystem_users"))


# Ensure that the auto post_syncdb hook is installed
# before our hook, so that Permission objects will be there
# by the time we are called.
import django.contrib.auth.management
