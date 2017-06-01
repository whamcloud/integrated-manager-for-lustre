# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
        return "fake_controller_%s.json" % self.controller_id

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
