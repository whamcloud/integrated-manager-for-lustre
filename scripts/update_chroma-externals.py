#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import sys
import re
import os
import json

from chroma_common.lib.shell import Shell


def gerrit_changes(user, change_id):
    changes = []

    for line in run_command(['ssh',
                             '-p',
                             '29418',
                             '%s@review.whamcloud.com' % user,
                             'gerrit query',
                             '--format', 'JSON',
                             '--patch-sets', change_id]).stdout.split('\n'):
        if line:
            change = json.loads(line.strip())

            # Only include the changes not the gerrit stats
            if 'type' not in change:
                changes.append(change)

    return changes


def run_command(args, exit_on_error=True):
    result = Shell.run(['time'] + args)

    if result.rc and exit_on_error:
        print "%s exited with error code %s, stdout %s" % (' '.join(args), result.rc, result.stderr)
        sys.exit(result.rc)

    print "%s returned %s:%s:%s" % (" ".join(args), result.rc, result.stdout, result.stderr)

    return result


def git_user():
    try:
        fetch_url = run_command(['bash', '-c', 'git remote show origin | grep "Fetch URL:"']).stdout
        user = re.search("Fetch URL: [a-z]*://([a-z]*)", fetch_url).groups()[0]
    except:
        user = 'hudson'

    print "Git user is %s" % user

    return user


def make_pristine():
    # Ensure that the submodules repository is absolutely pristine and unchanged. exit with rc !=0 if changes have occurred.

    # We can only make it pristine if it actually exists. It may be that there is not repo yet because we have only
    # done the git submodule init, so the repo is not truely in existence.
    if os.path.isdir('chroma-externals'):
        os.chdir('chroma-externals')
        run_command(['git', 'status'])
        run_command(['git', 'reset', '--hard'])
        run_command(['git', 'clean', '-dfx'])
        os.chdir('..')
    else:
        run_command(['git', 'submodule', 'init'])


def fetch_chroma_externals(user, externals_sha1):
    changes = gerrit_changes(user, externals_sha1)

    if not changes:
        print "Unable to find git commit for chroma-externals sha1 %s" % externals_sha1
        sys.exit(-1)

    # Find the patch set ref
    try:
        ref = next(change['ref'] for change in changes[0]['patchSets'] if change['revision'] == externals_sha1)
    except StopIteration:
        print "Unable to find gerrit patchset for chroma-externals sha1 %s" % externals_sha1
        sys.exit(-1)

    # Now fetch the appropriate sha1 from gerrit.
    os.chdir('chroma-externals')
    run_command(['git',
                 'fetch',
                 'ssh://%s@review.whamcloud.com:29418/chroma-externals' % user,
                 ref])
    run_command(['git', 'checkout', 'FETCH_HEAD'])
    os.chdir('..')

    # Submodule init should now work just fine.
    run_command(['git', 'submodule', 'update'])


def main():
    make_pristine()

    fetch_externals = run_command(['git', 'submodule', 'update'], False)

    if fetch_externals.rc:
        if 'fatal: reference is not a tree' not in fetch_externals.stderr:
            print "git submodule update returned an unexpected error."
            print "rc=%s" % fetch_externals.rc
            print "stdout=%s" % fetch_externals.stdout
            print "stderr=%s" % fetch_externals.stderr
            sys.exit(-1)

        user = git_user()

        externals_sha1_re = re.search('fatal: reference is not a tree: ([a-z0-9]+)', fetch_externals.stderr)
        externals_sha1 = externals_sha1_re.groups()[0]

        fetch_chroma_externals(user, externals_sha1)

# End of functions, start of execution.

main()
