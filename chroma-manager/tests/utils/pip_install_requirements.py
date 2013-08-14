#
# Simple script to pip install requirements in requirements.txt from a local directory.
#
# Usage: ./pip_install_requirements.py pip_packages_dir

import datetime
import os
import re
import sys
import subprocess
import time


class PipInstallRequirements(object):

    # The max amount of time we will continue trying to install.
    PIP_TIMEOUT = datetime.timedelta(hours=1)

    def __init__(self, pip_packages_dir, *args, **kwargs):
        super(PipInstallRequirements, self).__init__(*args, **kwargs)
        self.pip_packages_dir = pip_packages_dir

    def install(self):
        # Prepare the requirements.txt file
        subprocess.check_call(['make', 'requirements'])
        requirements = open('requirements.txt')

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

        if not os.path.exists(self.pip_packages_dir):
            # We haven't created our dir to cache pip packages yet
            # (ex, first run on a new builder). Create and seed.
            os.makedirs(self.pip_packages_dir)
            start_time = datetime.datetime.now()
            while datetime.datetime.now() - start_time < self.PIP_TIMEOUT:
                exit_status = subprocess.call(['pip', 'install', '--no-install',
                    '--download', self.pip_packages_dir, '--build', build_dir,
                    '-r', 'requirements.txt'])
                if exit_status == 0:
                    break
                else:
                    print "Error downloading packages. Will try again in 1 min."
                    time.sleep(60)
            if datetime.datetime.now() - start_time >= self.PIP_TIMEOUT:
                print "Timed out trying to download packages."
                sys.exit(1)

        # Determine which requirements cannot be fulfilled from the packages dir
        dependency_changes = []
        for line in requirements:
            line = line.strip()
            if line and not line[0] == '#':
                if re.match("[a-zA-Z]*://", line):
                    # The url based requirements, such as those from GitHub,
                    # need slightly different handling. They will still try
                    # to reach out to their external dependency even if it is
                    # in the package dir as --no-index only tells it not to
                    # talk to PyPi, not other sites. It will, however, use the
                    # previously downloaded package if we give it the exact
                    # location instead of just the line from requirements.txt.
                    expected_package_location = os.path.join(
                        self.pip_packages_dir,
                        line.rsplit('/', 1)[-1]
                    )
                    if os.path.exists(expected_package_location):
                        subprocess.check_call(['pip', 'install',
                            '--build', build_dir, '--no-index',
                            expected_package_location])
                    else:
                        dependency_changes.append(line)
                else:
                    exit_status = subprocess.call(['pip', 'install',
                        '--build', build_dir, '--no-index',
                        '--find-links', self.pip_packages_dir, line])
                    if not exit_status == 0:
                        dependency_changes.append(line)

        # If there are any requirements that cannot be fulilled from the packages
        # dir, download them.
        if dependency_changes:
            print "Downloading the following packages: %s" % ' '.join(dependency_changes)
            start_time = datetime.datetime.now()
            while datetime.datetime.now() - start_time < self.PIP_TIMEOUT:
                download_command = ['pip', 'install', '--no-install',
                    '--build', build_dir, '--download', self.pip_packages_dir]
                download_command.extend(dependency_changes)
                exit_status = subprocess.call(download_command)
                if exit_status == 0:
                    break
                else:
                    print "Error downloading packages. Will try again in 1 min."
                    time.sleep(60)
            if datetime.datetime.now() - start_time >= self.PIP_TIMEOUT:
                print "Timed out trying to download packages."
                sys.exit(1)
            print "Downloading complete. Installing..."
            # Install the newly downloaded requirements
            install_command = ['pip', 'install', '--no-index',
                '--build', build_dir, '--find-links', self.pip_packages_dir]
            install_command.extend(dependency_changes)
            subprocess.check_call(install_command)

        # One last check to make sure we meet all of the requirements in the
        # full requirements.txt now
        subprocess.check_call(['pip', 'install', '--quiet', '--no-index',
            '--build', build_dir, '--no-download',
            '--find-links', self.pip_packages_dir, '-r', 'requirements.txt'])
        print 'SUCCESS'


if __name__ == '__main__':
    pip_packages_dir = sys.argv[1]
    installer = PipInstallRequirements(pip_packages_dir)
    installer.install()
