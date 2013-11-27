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


from optparse import make_option
import tarfile
from chroma_core.lib.util import site_dir
import os
import sys

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

        # default, works for --no-bundles
        base_profile_path = os.path.join(site_dir(), "../chroma-bundles/base_managed.profile")

        if options['no_bundles']:
            for bundle in ['lustre', 'lustre-client', 'iml-agent', 'e2fsprogs']:
                Bundle.objects.get_or_create(bundle_name=bundle, location="/tmp/", description="Dummy bundle")
        else:
            # override the default path if we have unpacked a real archive
            repo_profile_path = os.path.join(settings.DEV_REPO_PATH, 'base_managed.profile')
            if os.path.isfile(repo_profile_path):
                base_profile_path = repo_profile_path

            import json
            import glob
            with open(base_profile_path) as f:
                bundle_names = json.load(f)['bundles']
            missing_bundles = bundle_names

            bundle_files = glob.glob(os.path.join(settings.DEV_REPO_PATH, "*-bundle.tar.gz"))
            for bundle_file in bundle_files:
                archive = tarfile.open(bundle_file, "r:gz")
                meta = json.load(archive.extractfile("./meta"))
                repo = os.path.join(settings.DEV_REPO_PATH, meta['name'])

                if not os.path.exists(os.path.join(repo, 'meta')):
                    print "Extracting %s" % meta['name']
                    if not os.path.exists(repo):
                        os.makedirs(repo)

                    #archive.list()
                    archive.extractall(repo)
                    archive.close()

                if not Bundle.objects.filter(location=repo).exists():
                    chroma_core.lib.service_config.bundle('register', repo)

                try:
                    missing_bundles.remove(meta['name'])
                except ValueError:
                    # Bundles not associated with a profile are OK
                    pass

            if len(missing_bundles):
                print """
Missing bundles: %(bundles)s

Package bundles are required for installation. In order to proceed, you
have 3 options:
    1. Download an installer from %(bundle_url)s and unpack it in %(repo_path)s
    2. Build an installer locally and unpack it in %(repo_path)s
    3. Run ./manage.py dev_setup --no-bundles to generate a set of fake
       bundles for simulated servers

Please note that the fake bundles can't be used to install real storage
servers -- you'll need to use one of the first two methods in order to make
that work.
    """ % {'bundle_url': "http://build.whamcloudlabs.com/job/chroma/arch=x86_64,distro=el6.4/lastSuccessfulBuild/artifact/chroma-bundles/", 'repo_path': settings.DEV_REPO_PATH, 'bundles': ", ".join(missing_bundles)}
                sys.exit(1)

        for name in ('base_managed', 'base_monitored', 'posix_copytool_worker'):
            base_profile_path = os.path.join(os.path.dirname(base_profile_path), name + '.profile')
            if not ServerProfile.objects.filter(name=name).exists():
                chroma_core.lib.service_config.register_profile(open(base_profile_path))

        print """Great success:
 * run `./manage.py supervisor`
 * open %s""" % settings.SERVER_HTTP_URL
