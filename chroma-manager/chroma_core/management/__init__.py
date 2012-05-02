#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.contrib.auth.models import User
from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
import django.contrib.auth as auth
import settings

from chroma_core.models import ManagedHost, ManagedTarget, ManagedFilesystem, StorageResourceRecord
from chroma_core.models import Job, Command, Volume, VolumeNode


def setup_groups(sender, **kwargs):
    if auth.models.Group.objects.count() == 0:
        print "Creating groups..."
        auth.models.Group.objects.create(name = "superusers")
        fsadmin_group = auth.models.Group.objects.create(name = "filesystem_administrators")

        def grant_write(group, model):
            for perm in auth.models.Permission.objects.filter(content_type = ContentType.objects.get_for_model(model)):
                group.permissions.add(perm)

        grant_write(fsadmin_group, ManagedTarget)
        grant_write(fsadmin_group, ManagedHost)
        grant_write(fsadmin_group, ManagedFilesystem)
        grant_write(fsadmin_group, StorageResourceRecord)
        grant_write(fsadmin_group, Job)
        grant_write(fsadmin_group, Command)
        grant_write(fsadmin_group, Volume)
        grant_write(fsadmin_group, VolumeNode)
        grant_write(fsadmin_group, User)

        fsusers_group = auth.models.Group.objects.create(name = "filesystem_users")
        # For modifying his own account
        grant_write(fsusers_group, User)

    if settings.DEBUG and auth.models.User.objects.count() == 0:
        print "***\n" * 3,
        print "*** SECURITY WARNING: You are running in DEBUG mode and default users have been created"
        print "***\n" * 3
        user = auth.models.User.objects.create_superuser("debug", "debug@debug.co.eh", "chr0m4_d3bug")
        user.groups.add(auth.models.Group.objects.get(name='superusers'))
        user = auth.models.User.objects.create_superuser("admin", "admin@debug.co.eh", "chr0m4_d3bug")
        user.groups.add(auth.models.Group.objects.get(name='filesystem_administrators'))


post_syncdb.connect(setup_groups, sender=auth.models)
