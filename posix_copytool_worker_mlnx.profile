{
  "ui_name": "POSIX HSM Agent Node (MLNX)",
  "managed": true,
  "worker": true,
  "name": "posix_copytool_worker",
  "initial_state": "working",
  "ntp": true,
  "corosync": false,
  "corosync2": false,
  "pacemaker": false,
  "ui_description": "An HSM agent node using the POSIX copytool, with Mellanox IB support",
  "packages": [
    "python2-iml-agent-management",
    "mlnx-ofa_kernel-devel",
    "kmod-mlnx-ofa_kernel",
    "lustre-client"
  ],
  "repolist": [
    "base",
    "lustre-client-mlnx"
  ]
}
