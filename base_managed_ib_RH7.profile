{
    "ui_name": "Managed Storage Server (MLNX)",
    "managed": true,
    "worker": false,
    "name": "base_managed_ib_rh7",
    "initial_state": "managed",
    "ntp": true,
    "corosync": false,
    "corosync2": true,
    "pacemaker": true,
    "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets using Mellanox OFED",
    "packages": [
        "python2-iml-agent-management",
        "kernel-devel-lustre",
        "pcs",
        "fence-agents",
        "fence-agents-virsh",
        "mlnx-ofa_kernel-devel",
        "kmod-mlnx-ofa_kernel",
        "lustre-resource-agents",
        "lustre-ldiskfs"
    ],
    "repolist": [
        "base",
        "lustre-server-mlnx"
    ],
    "validation": [
        {
            "description": "The profile is designed for version 7 of EL",
            "test": "distro_version < 8 and distro_version >= 7"
        }
    ]
}
