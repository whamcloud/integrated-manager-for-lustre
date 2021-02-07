# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from os import path
from datetime import datetime

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class EMF(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """EMF Framework"""

    plugin_name = "emf"
    profiles = ("lustre",)
    requires_root = True

    def setup(self):
        limit = self.get_option("log_size", default=None)
        all_logs = self.get_option("all_logs", default=False)
        tailit = self.get_option("tailit", default=False)

        copy_globs = ["/etc/emf/*.conf"]

        self.add_copy_spec(copy_globs, sizelimit=limit, tailit=tailit)

        self.add_cmd_output(
            [
                "emf server list",
                "emf target list",
                "emf filesystem list",
                "emf filesystem pool list",
                "emf-agent ha list",
                "lctl device_list",
                "lctl debug_kernel",
                "lctl list_nids",
                "blkid -s UUID -s TYPE",
                "df --all",
                "ps -ef --forest",
                "cibadmin --query",
            ]
        )

        time_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        db_file_name = "emfdb_%s.sql.gz" % time_stamp
        db_dest = path.join(self.get_cmd_output_path(), db_file_name)

        cmd = "pg_dump -U emf -F p -Z 9 -w -f %s -T logmessage* emf" % db_dest

        self.add_cmd_output(cmd, chroot=self.tmp_in_sysroot())


# vim: set et ts=4 sw=4 :
