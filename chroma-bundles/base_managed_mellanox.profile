{
  "ui_name": "Managed storage server with Mellanox OFED", 
  "managed": true, 
  "name": "base_managed_mellanox", 
  "bundles": [
    "iml-agent", 
    "lustre-mellanox", 
    "e2fsprogs"
  ], 
  "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets with Mellanox OFED", 
  "packages": {
    "lustre-mellanox": [
      "kernel-ib",
      "lustre-modules",
      "lustre"
    ]
  }
}
