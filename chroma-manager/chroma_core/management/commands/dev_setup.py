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


from StringIO import StringIO
from optparse import make_option
import tarfile
from chroma_core.lib.util import site_dir
import os

from django.core.management import BaseCommand
import settings


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--no-bundles',
                    action='store_true',
                    dest='no_bundles',
                    default=False,
                    help='Do not load any bundles, instead create dummies for use with simulator'),
    )

    def handle(self, *args, **options):
        from chroma_core.lib.service_config import ServiceConfig

        sc = ServiceConfig()
        sc._setup_rabbitmq_credentials()
        sc._setup_crypto()
        sc._syncdb()

        import chroma_core.lib.service_config
        from chroma_core.models import Bundle, ServerProfile

        if options['no_bundles']:
            for bundle in ['lustre', 'chroma-agent', 'e2fsprogs']:
                Bundle.objects.get_or_create(bundle_name=bundle, location="/tmp/", description="Dummy bundle")
        else:
            import json
            with open(os.path.join(settings.DEV_REPO_PATH, 'base_managed.profile')) as f:
                bundle_names = json.load(f)['bundles']
            missing_bundles = []
            for bundle_name in bundle_names:
                path = os.path.join(settings.DEV_REPO_PATH, bundle_name)
                if not os.path.exists(os.path.join(path, 'meta')):
                    tarball_path = os.path.join(settings.DEV_REPO_PATH, bundle_name) + "-bundle.tar.gz"
                    if os.path.exists(tarball_path):
                        print "Extracting %s" % bundle_name
                        if not os.path.exists(path):
                            os.makedirs(path)
                        archive = tarfile.open(tarball_path, "r:gz")
                        archive.list()
                        archive.extractall(path)
                    else:
                        print "Missing bundle %s" % bundle_name
                        missing_bundles.append(path)

                if (not path in missing_bundles and
                    not Bundle.objects.filter(location=path).exists()):
                    chroma_core.lib.service_config.bundle('register', path)

            if len(missing_bundles):
                print """
Package bundles are required for installation. In order to proceed, you
have 3 options:
    1. Download a bundle from %(bundle_url)s and unpack it in %(repo_path)s
    2. Build a bundle locally and unpack it in %(repo_path)s
    3. Run ./manage.py dev_setup --no-bundles to generate a set of fake
       bundles for simulated servers

Please note that the fake bundles can't be used to install real storage
servers -- you'll need to use one of the first two methods in order to make
that work.
    """ % {'bundle_url': "http://build.whamcloudlabs.com/job/chroma/arch=x86_64,distro=el6.4/lastSuccessfulBuild/artifact/chroma-bundles/", 'repo_path': settings.DEV_REPO_PATH}
                return

        if os.path.exists(os.path.join(settings.DEV_REPO_PATH, 'base_managed.profile')):
            base_profile_path = os.path.join(settings.DEV_REPO_PATH, 'base_managed.profile')
        else:
            base_profile_path = os.path.join(site_dir(), "../chroma-bundles/base_managed.profile.template")
        base_profile = open(base_profile_path).read()
        if not ServerProfile.objects.filter(name='base_managed').exists():
            chroma_core.lib.service_config.register_profile(StringIO(base_profile))

        print """Great success:
 * run `./manage.py supervisor`
 * open %s""" % settings.SERVER_HTTP_URL
