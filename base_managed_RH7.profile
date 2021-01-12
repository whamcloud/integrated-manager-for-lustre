{
    "ui_name": "Managed Storage Server",
    "managed": true,
    "worker": false,
    "name": "base_managed_rh7",
    "initial_state": "managed",
    "ntp": true,
    "corosync": false,
    "corosync2": true,
    "pacemaker": true,
    "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
    "packages": [
        "python2-emf-agent-management",
        "kernel-devel-lustre",
        "pcs",
        "lustre-resource-agents",
        "lustre-ldiskfs"
    ],
    "repolist": [
        "base",
        "lustre-server"
    ],
    "validation": [
        {
            "description": "The profile is designed for version 7 of EL",
            "test": "distro_version < 8 and distro_version >= 7"
        }
    ]
}
