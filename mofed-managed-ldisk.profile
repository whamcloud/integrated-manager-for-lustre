{
  "ui_name": "Managed Mellanox OFED ldiskfs Storage Server",
  "managed": true,
  "worker": false,
  "name": "mofed_managed_ldiskfs",
  "initial_state": "managed",
  "ntp": true,
  "corosync": false,
  "corosync2": true,
  "pacemaker": true,
  "bundles": [
    "external"
  ],
  "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
  "packages": {
    "external": [
      "python2-iml-agent-management",
      "kernel-devel-lustre",
      "lustre-ldiskfs-zfs"
    ]
  },
  "validation": [
    {"test": "distro_version < 8 and distro_version >= 7", "description": "The profile is designed for version 7 of EL"}
  ]
}
