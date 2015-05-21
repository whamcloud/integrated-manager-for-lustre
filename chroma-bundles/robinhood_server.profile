{
  "ui_name": "Robinhood Policy Engine Server",
  "managed": true,
  "worker": true,
  "name": "robinhood_server",
  "bundles": [
    "iml-agent",
    "lustre-client",
    "robinhood"
  ],
  "ui_description": "A server running the Robinhood Policy Engine",
  "packages": {
    "lustre-client": [
      "lustre-client-modules",
      "lustre-client"
    ],
    "robinhood": [
      "robinhood-lhsm",
      "robinhood-webgui",
      "robinhood-adm"
    ]
  },
  "validation": [
    {"test": "distro_version < 7 and distro_version >= 6", "description": "Only version 6 of EL is supported by the Robinhood Policy Engine Server profile"}
  ]
}
