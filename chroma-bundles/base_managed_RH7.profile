{
  "ui_name": "Managed Storage Server For EL7.2",
  "managed": true,
  "worker": false,
  "name": "base_managed_rh7",
  "initial_state": "managed",
  "rsyslog": true,
  "ntp": true,
  "corosync": false,
  "corosync2": true,
  "pacemaker": true,
  "bundles": [
    "iml-agent",
    "lustre",
    "e2fsprogs"
  ],
  "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
  "packages": {
    "lustre": [
      "lustre-modules",
      "lustre-osd-ldiskfs",
      "lustre"
    ]
  },
  "validation": [
    {"test": "zfs_installed == False", "description": "ZFS is installed but is unsupported by the Managed Storage Server profile"},
    {"test": "distro_version < 8 and distro_version >= 7", "description": "The profile is designed for version 7 of EL"}
  ]
}
