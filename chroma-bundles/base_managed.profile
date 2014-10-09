{
  "ui_name": "Managed storage server", 
  "managed": true,
  "worker": false,
  "name": "base_managed", 
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
    {"test": "zfs_installed == False", "description": "ZFS is installed but is unsupported by the Managed storage server profile"}
  ]
}
