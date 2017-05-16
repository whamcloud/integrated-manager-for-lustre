{
  "ui_name": "POSIX HSM Agent Node",
  "managed": true,
  "worker": true,
  "name": "posix_copytool_worker",
  "initial_state": "working",
  "rsyslog": true,
  "ntp": true,
  "corosync": false,
  "corosync2": false,
  "pacemaker": false,
  "bundles": [
    "iml-agent",
    "external"
  ],
  "ui_description": "An HSM agent node using the POSIX copytool",
  "packages": {
    "iml-agent": [
      "chroma-agent-management"
    ],
    "external": [
      "lustre-client"
    ]
  }
}
