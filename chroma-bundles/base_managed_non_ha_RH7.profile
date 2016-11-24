{
  "ui_name": "Managed Non-HA Storage Server",
  "managed": true,
  "worker": false,
  "name": "base_managed_non_ha_rh7",
  "initial_state": "managed",
  "rsyslog": true,
  "ntp": true,
  "corosync": false,
  "corosync2": false,
  "pacemaker": false,
  "bundles": [
    "iml-agent",
    "lustre",
    "e2fsprogs",
    "zfs"
  ],
  "ui_description": "A storage server suitable for creating new non-HA filesystem targets",
  "packages": {
    "iml-agent": [
      "chroma-agent-management"
    ],
    "lustre": [
      "lustre",
      "lustre-modules",
      "lustre-osd-ldiskfs",
      "lustre-osd-zfs",
      "kernel-devel-3.10.0-514.el7_lustre"
    ],
    "zfs": [
      "zfs"
    ]
  },
  "validation": [
    {"test": "distro_version < 8 and distro_version >= 7", "description": "The profile is designed for version 7 of EL"}
  ]
}
