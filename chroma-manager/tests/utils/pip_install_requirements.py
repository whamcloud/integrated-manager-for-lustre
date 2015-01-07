#
# Simple script to pip install requirements in requirements.txt from a local directory.
#
# Usage: ./pip_install_requirements.py pip_packages_dir

import datetime
import os
import re
import sys
import subprocess


class PipInstallRequirements(object):

    # The max amount of time we will continue trying to install.
    PIP_TIMEOUT = datetime.timedelta(hours=1)

    def __init__(self, pip_packages_dir, packages_to_install, *args, **kwargs):
        super(PipInstallRequirements, self).__init__(*args, **kwargs)
        self.pip_packages_dir = pip_packages_dir
        self.packages_to_install = packages_to_install or open('requirements.txt')

    def install(self):
        virtual_env = os.environ.get('VIRTUAL_ENV')
        print "VIRTUAL_ENV=%s" % virtual_env
        if not virtual_env:
            # Protect against accidental use outside of a virtualenv,
            # polluting the local system.
            print "This script was designed to be used inside of a virtualenv only."
        # Explicitly stating the build dir helps ensure we don't accidentally
        # use /tmp instead, which can fill quickly on builders.
        build_dir = os.path.join(virtual_env, 'build')
        print "BUILD_DIR=%s" % build_dir

        for package in self.packages_to_install:
            package = package.strip()
            if package and not package[0] == '#':
                if re.match("https?://", package):
                    # The url based requirements, such as those from GitHub,
                    # need slightly different handling. They will still try
                    # to reach out to their external dependency even if it is
                    # in the package dir as --no-index only tells it not to
                    # talk to PyPi, not other sites. It will, however, use the
                    # previously downloaded package if we give it the exact
                    # location instead of just the package description.
                    expected_package_location = os.path.join(
                        self.pip_packages_dir,
                        package.rsplit('/', 1)[-1]
                    )
                    if os.path.exists(expected_package_location):
                        subprocess.check_call(['pip', 'install',
                                               '--build', build_dir, '--no-index', '--pre',
                                               expected_package_location])
                    else:
                        print "Failed to install %s" % package.rsplit('/', 1)[-1]
                        sys.exit(1)
                else:
                    exit_status = subprocess.call(['pip', 'install',
                                                   '--build', build_dir, '--no-index', '--pre',
                                                   '--find-links', 'file://%s' % self.pip_packages_dir, package])
                    if not exit_status == 0:
                        print "Failed to install %s" % package
                        sys.exit(1)


if __name__ == '__main__':
    installer = PipInstallRequirements(sys.argv[1], sys.argv[2:])
    installer.install()
