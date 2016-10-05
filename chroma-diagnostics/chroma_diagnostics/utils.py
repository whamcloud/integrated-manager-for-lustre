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

import subprocess
import os


def run_command(cmd, out, err):
    try:
        p = subprocess.Popen(cmd, stdout = out, stderr = err)
    except OSError:
        #  The cmd in this case could not run, skipping
        return None
    else:
        p.wait()
        try:
            out.flush()
        except AttributeError:
            # doesn't do flush
            pass
        try:
            err.flush()
        except AttributeError:
            # doesn't do flush
            pass
        return p


def run_command_output_piped(cmd):
    return run_command(cmd, subprocess.PIPE, subprocess.PIPE)


def save_command_output(fn, cmd, output_directory):

    out_fn = "%s.out" % fn
    err_fn = "%s.err" % fn
    out_path = os.path.join(output_directory, out_fn)
    err_path = os.path.join(output_directory, err_fn)

    with open(out_path, 'w') as out:
        with open(err_path, 'w') as err:
            result = run_command(cmd, out, err)

    # Remove meaningless zero lenth error files
    if os.path.getsize(err_path) <= 0:
        os.remove(err_path)

    return result


def change_tree_permissions(root_directory, new_permission):
    """Change the permissions of all the files and directories below and
    including the root_directory passed.
    root_directory: Root to directory tree to change permissions of.
    new_permission: Permission value to set.
    """
    for root, dirs, files in os.walk(root_directory):
        for cd_file in files:
            path = os.path.join(root, cd_file)
            if os.path.exists(path):
                os.chmod(os.path.join(root, cd_file), new_permission)
