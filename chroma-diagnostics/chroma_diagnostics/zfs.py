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

import logging
import os

import utils

log = logging.getLogger(__name__)


def get_zdb_output_for_zpools(parent_directory, verbose):
    zpool_list = utils.run_command_output_piped(['zfs', 'list', '-H', '-o', 'name']).stdout.read().strip().split()
    output_dir = os.path.join(parent_directory, 'zdb_output')
    os.mkdir(output_dir)
    log.info('Examining pools and datasets')

    for zpool_name in zpool_list:
        if utils.save_command_output(zpool_name, ['zdb', '-e', zpool_name], output_dir):
            log.info('Display information of %s' % zpool_name)
        elif verbose > 0:
            log.info('Error Displaying information of %s' % zpool_name)


def check_and_display_hostid(parent_directory, verbose):
    log.info('Performing checks on /etc/hostid')
    output_dir = os.path.join(parent_directory, 'etc_hostid_output')
    os.mkdir(output_dir)

    if utils.run_command_output_piped(['ls', '/etc/hostid']).returncode != 0:
        log.info('File /etc/hostid not found')
    elif os.path.getsize('/etc/hostid') <= 0:
        log.info('File /etc/hostid is empty')
    else:
        log.info('Checks on /etc/hostid passed')
        if utils.save_command_output('etc_hostid', ['od', '-An', '-vtx1', '/etc/hostid'], output_dir):
            log.info('Convert /etc/hostid')
        elif verbose > 0:
            log.info('Error converting /etc/hostid')
