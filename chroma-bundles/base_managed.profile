{
  "ui_name": "Managed storage server", 
  "managed": true, 
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
      "lustre"
    ]
  }
}
