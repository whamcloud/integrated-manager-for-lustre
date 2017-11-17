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
  "bundles": [
  ],
  "ui_description": "A server running the Robinhood Policy Engine",
  "packages": {
    "external": [
      "chroma-agent-management",
      "lustre-client",
      "robinhood-lhsm",
      "robinhood-webgui",
      "robinhood-adm"
    ]
  }
}
