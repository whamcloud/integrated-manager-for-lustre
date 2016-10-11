{
  "ui_name": "Managed Storage Server",
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
    "e2fsprogs",
    "zfs"
  ],
  "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
  "packages": {
    "iml-agent": [
      "chroma-agent-management"
    ],
    "lustre": [
      "lustre",
      "lustre-modules",
      "lustre-osd-ldiskfs",
      "lustre-osd-zfs",
      "kernel-devel-3.10.0-327.28.2.el7_lustre"
    ],
    "zfs": [
      "zfs"
    ]
  },
  "validation": [
    {"test": "distro_version < 8 and distro_version >= 7", "description": "The profile is designed for version 7 of EL"}
  ]
}
