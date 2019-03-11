{
  "ui_name": "POSIX HSM Agent Node",
  "managed": true,
  "worker": true,
  "name": "posix_copytool_worker",
  "initial_state": "working",
  "ntp": true,
  "corosync": false,
  "corosync2": false,
  "pacemaker": false,
  "ui_description": "An HSM agent node using the POSIX copytool",
  "packages": [
    "python2-iml-agent-management",
    "lustre-client"
  ],
  "repolist": [
    "base",
    "lustre-client"
  ]
}
