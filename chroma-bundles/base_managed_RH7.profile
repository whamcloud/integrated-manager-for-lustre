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
    "external"
  ],
  "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
  "packages": {
    "iml-agent": [
      "chroma-agent-management"
    ],
    "external": [
      "lustre-dkms",
      "lustre-osd-ldiskfs-mount",
      "lustre-osd-zfs-mount",
      "kernel-*_lustre",
      "kernel-devel-*_lustre",
      "zfs"
    ]
  },
  "validation": [
    {"test": "distro_version < 8 and distro_version >= 7", "description": "The profile is designed for version 7 of EL"}
  ]
}
