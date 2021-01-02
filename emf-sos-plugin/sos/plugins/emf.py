# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from os import path
from datetime import datetime

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class EMF(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """EMF Framework"""

    plugin_name = "iml"
    profiles = ("lustre",)
    requires_root = True

    def setup(self):
        limit = self.get_option("log_size", default=None)
        all_logs = self.get_option("all_logs", default=False)
        tailit = self.get_option("tailit", default=False)

        if all_logs:
            copy_globs = [
                "/var/log/chroma/",
                "/var/log/chroma-agent*",
            ]
        else:
            copy_globs = [
                "/var/log/chroma/*.log",
                "/var/log/chroma-agent*.log",
            ]

        copy_globs += [
            "/etc/iml/*.conf",
            "/var/lib/chroma/*.conf",
            "/var/lib/chroma/settings/*",
            "/var/lib/chroma/targets/*",
        ]

        self.add_copy_spec(copy_globs, sizelimit=limit, tailit=tailit)

        self.add_cmd_output(
            [
                "chroma-agent device_plugin --plugin=linux",
                "chroma-agent detect_scan",
                "chroma-config validate",
                "chroma-agent device_plugin --plugin=linux_network",
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
        db_file_name = "chromadb_%s.sql.gz" % time_stamp
        db_dest = path.join(self.get_cmd_output_path(), db_file_name)

        cmd = (
            "pg_dump -U chroma -F p -Z 9 -w -f %s -T chroma_core_logmessage* -T chroma_core_series* -T chroma_core_sample_* chroma"
            % db_dest
        )

        self.add_cmd_output(cmd, chroot=self.tmp_in_sysroot())


# vim: set et ts=4 sw=4 :
