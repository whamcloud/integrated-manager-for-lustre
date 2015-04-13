{
  "ui_name": "POSIX HSM Agent Node",
  "managed": true,
  "worker": true,
  "name": "posix_copytool_worker",
  "initial_state": "working",
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
  },
  "validation": [
    {"test": "distro_version < 7 and distro_version >= 6", "description": "Only version 6 of EL is supported by the Copytool Worker profile"}
  ]
}
