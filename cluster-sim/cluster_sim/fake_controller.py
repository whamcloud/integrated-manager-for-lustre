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


from copy import deepcopy
import traceback
import uuid
from cluster_sim.utils import Persisted


class FakeController(Persisted):
    default_state = {
        'controller_id': None,
        'luns': {},
        'disks': {}
    }

    @property
    def filename(self):
        return "fake_controller_%s" % self.controller_id

    def __init__(self, path, controller_id):
        self.controller_id = controller_id

        super(FakeController, self).__init__(path)

        self.state['controller_id'] = controller_id
        self.save()

    def add_lun(self, serial, size):
        if serial in self.state['luns']:
            raise RuntimeError("A lun with serial '%s' already exists" % serial)

        wwids = []
        disk_count = 10
        disk_size = size / (disk_count - 2)  # RAID6
        for disk in range(0, disk_count):
            wwid = uuid.uuid4().__str__()
            self.state['disks'][wwid] = {
                'wwid': wwid,
                'size': disk_size
            }
            wwids.append(wwid)

        self.state['luns'][serial] = {
            'serial': serial,
            'size': size,
            'wwids': wwids
        }

        self.save()

    def poll(self):
        try:
            data = deepcopy(self.state)
            # Annoyingly, XMLRPC doesn't like big integers: work around by sending megabytes instead of bytes
            for lun_serial, lun_data in data['luns'].items():
                lun_data['size'] /= 1024 * 1024

            for disk_wwid, disk_data in data['disks'].items():
                disk_data['size'] /= 1024 * 1024

            return data
        except Exception:
            print traceback.format_exc()
            raise
