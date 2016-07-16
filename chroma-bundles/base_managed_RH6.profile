{
  "ui_name": "Managed Storage Server for EL6.7",
  "managed": true,
  "worker": false,
  "name": "base_managed",
  "initial_state": "managed",
  "rsyslog": true,
  "ntp": true,
  "corosync": true,
  "corosync2": false,
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
    {"test": "distro_version < 7 and distro_version >= 6", "description": "The profile is designed for version 6 of EL"}
  ]
}
