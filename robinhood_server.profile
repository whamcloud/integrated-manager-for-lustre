{
  "ui_name": "Robinhood Policy Engine Server",
  "managed": true,
  "worker": true,
  "name": "robinhood_server",
  "initial_state": "working",
  "ntp": true,
  "corosync": false,
  "corosync2": false,
  "pacemaker": false,
  "ui_description": "A server running the Robinhood Policy Engine",
  "packages": [
    "python2-iml-agent-management",
    "lustre-client",
    "robinhood-lhsm",
    "robinhood-webgui",
    "robinhood-adm"
  ],
  "repolist": [
    "base",
    "lustre-client"
  ]
}
