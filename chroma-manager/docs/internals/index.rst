
Chroma internals
================

This is documentation internal to the Chroma engineering team, mostly generated from docstrings
in the code.

Chroma is split into the *agent* and the *manager*.  The manager is the central
monitoring service, while an instance of the agent runs on each Lustre server
(aka Chroma Storage Server) reporting back to the central manager.

.. toctree::
  :maxdepth: 2

  manager/index
  agent/index
  cluster_sim

Components
==========

.. graphviz::

    graph toplevel_components {
        compound=true;
        node [style=filled];
        subgraph cluster_manager_server {
            subgraph cluster_chroma_manager {
                label="chroma-manager";
                labelloc=b;
                "chroma_api";
                "chroma_api" -- "chroma_core";
                "chroma_ui" -- "chroma_api";
                "chroma_cli" -- "chroma_api";
            }
            label="Manager server (Linux)";
            labelloc=b;
            "chroma_core" -- "3rd party storage plugin"
            "chroma_core" -- "RabbitMQ";
            "chroma_core" -- "PostgreSQL";
        }

        "User (browser)" -- "chroma_ui";
        "User (shell)" -- "chroma_cli";
        "3rd party tool" -- "chroma_api";
        "3rd party storage plugin" -- "3rd party storage controller"
        "devicemapper" -- "3rd party storage controller" [ltail=cluster_storage_server]

        subgraph cluster_storage_server {
            label="Storage server (Linux)"
            labelloc=b;
            "chroma-agent" -- "Corosync/Pacemaker"
            "chroma-agent" -- "Lustre"
            "chroma-agent" -- "/proc/"
            "chroma-agent" -- "rpm/yum"
            "chroma-agent" -- "devicemapper"
        }

        "chroma-agent" -- chroma_core [lhead=cluster_chroma_manager,label=HTTPS]
    }
