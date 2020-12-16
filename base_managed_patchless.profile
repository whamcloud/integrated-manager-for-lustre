{
    "ui_name": "Managed Storage Server (patchless)",
    "managed": true,
    "worker": false,
    "name": "base_managed_patchless",
    "initial_state": "managed",
    "ntp": true,
    "corosync": false,
    "corosync2": true,
    "pacemaker": true,
    "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
    "packages": [
        "python2-iml-agent-management",
        "pcs",
        "fence-agents",
        "fence-agents-virsh",
        "lustre-resource-agents",
        "lustre-ldiskfs"
    ],
    "repolist": [
        "base",
        "lustre-server-patchless"
    ],
    "validation": [
        {
            "description": "The profile is designed for version 7.7 of EL",
            "test": "distro_version < 7.8 and distro_version > 7.6"
        }
    ]
}
