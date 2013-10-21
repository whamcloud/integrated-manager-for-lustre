#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import django.contrib.auth.models
from django.contrib.contenttypes.models import ContentType
import django.contrib.auth as auth
from south.signals import post_migrate

import chroma_core.models

import settings


def setup_groups(app, **kwargs):
    if app != 'chroma_core':
        return

    if auth.models.Group.objects.count() == 0:
        print "Creating groups..."
        auth.models.Group.objects.create(name = "superusers")
        fsadmin_group = auth.models.Group.objects.create(name = "filesystem_administrators")

        def grant_write(group, model):
            for perm in auth.models.Permission.objects.filter(content_type = ContentType.objects.get_for_model(model)):
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
        for alert_klass in all_subclasses(chroma_core.models.AlertState):
            grant_write(fsadmin_group, alert_klass)

        # Allow fs admins to dismiss events
        grant_write(fsadmin_group, chroma_core.models.Event)
        for alert_klass in all_subclasses(chroma_core.models.Event):
            grant_write(fsadmin_group, alert_klass)

        fsusers_group = auth.models.Group.objects.create(name = "filesystem_users")
        # For modifying his own account
        grant_write(fsusers_group, django.contrib.auth.models.User)

    if settings.DEBUG and auth.models.User.objects.count() == 0:
        print "***\n" * 3,
        print "*** SECURITY WARNING: You are running in DEBUG mode and default users have been created"
        print "***\n" * 3
        user = auth.models.User.objects.create_superuser("debug", "debug@debug.co.eh", "chr0m4_d3bug")
        user.groups.add(auth.models.Group.objects.get(name='superusers'))
        user = auth.models.User.objects.create_user("admin", "admin@debug.co.eh", "chr0m4_d3bug")
        user.groups.add(auth.models.Group.objects.get(name='filesystem_administrators'))
        user = auth.models.User.objects.create_user("user", "user@debug.co.eh", "chr0m4_d3bug")
        user.groups.add(auth.models.Group.objects.get(name='filesystem_users'))


## Ensure that the auto post_syncdb hook is installed
## before our hook, so that Permission objects will be there
## by the time we are called.
import django.contrib.auth.management

post_migrate.connect(setup_groups)
