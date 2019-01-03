# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from optparse import make_option
import tarfile
from chroma_core.lib.util import site_dir
import os
import sys
import glob
import json

from django.core.management import BaseCommand
import settings


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            "--no-bundles",
            action="store_true",
            dest="no_bundles",
            default=False,
            help="Do not load any bundles, instead create dummies",
        ),
    )

    def handle(self, *args, **options):
        from chroma_core.lib import service_config
        from chroma_core.models import Bundle

        sc = service_config.ServiceConfig()
        sc._setup_rabbitmq_credentials()
        sc._setup_crypto()
        sc._syncdb()

        # default, works for --no-bundles
        profile_path = os.path.join(site_dir(), "../chroma-bundles/base_managed_RH7.profile")

        if options["no_bundles"]:
            for bundle in ["iml-agent", "external"]:
                Bundle.objects.get_or_create(bundle_name=bundle, location="/tmp/", description="Dummy bundle")
        else:
            # override the default path if we have unpacked a real archive
            repo_profile_path = os.path.join(settings.DEV_REPO_PATH, "base_managed_RH7.profile")
            if os.path.isfile(repo_profile_path):
                profile_path = repo_profile_path

            with open(profile_path) as f:
                bundle_names = json.load(f)["bundles"]
            missing_bundles = bundle_names

            bundle_files = glob.glob(os.path.join(settings.DEV_REPO_PATH, "*-bundle.tar.gz"))
            for bundle_file in bundle_files:
                archive = tarfile.open(bundle_file, "r:gz")
                meta = json.load(archive.extractfile("./meta"))
                repo = os.path.join(settings.DEV_REPO_PATH, meta["name"])

                if not os.path.exists(os.path.join(repo, "meta")):
                    print("Extracting %s" % meta["name"])
                    if not os.path.exists(repo):
                        os.makedirs(repo)

                    archive.extractall(repo)
                    archive.close()

                if not Bundle.objects.filter(location=repo).exists():
                    service_config.bundle("register", repo)

                try:
                    missing_bundles.remove(meta["name"])
                except ValueError:
                    # Bundles not associated with a profile are OK
                    pass

            if len(missing_bundles):
                print(
                    """
Missing bundles: %(bundles)s

Package bundles are required for installation. In order to proceed, you
have 2 options:
    1. Download an installer from %(bundle_url)s and unpack it in %(repo_path)s
    2. Build an installer locally and unpack it in %(repo_path)s

Please note that the fake bundles can't be used to install real storage
servers -- you'll need to use one of the first two methods in order to make
that work.
    """
                    % {
                        "bundle_url": "http://jenkins.lotus.hpdd.lab.intel.com/job/manager-for-lustre/arch=x86_64,distro=el7/lastSuccessfulBuild/artifact/chroma-bundles/",
                        "repo_path": settings.DEV_REPO_PATH,
                        "bundles": ", ".join(missing_bundles),
                    }
                )
                sys.exit(1)

        for profile_path in glob.glob(os.path.join(os.path.dirname(profile_path), "*.profile")):
            with open(profile_path) as profile_file:
                service_config.register_profile(profile_file)

        print(
            """Great success:
 * run `systemctl start iml-manager.target`
 * open %s"""
            % settings.SERVER_HTTP_URL
        )
