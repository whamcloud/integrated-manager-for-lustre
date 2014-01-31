{
  "ui_name": "POSIX HSM Agent Node",
  "managed": true,
  "worker": true,
  "name": "posix_copytool_worker",
  "bundles": [
    "iml-agent",
    "lustre-client"
  ],
  "ui_description": "An HSM agent node using the POSIX copytool",
  "packages": {
    "lustre-client": [
      "lustre-client-modules",
      "lustre-client"
    ]
  }
}
