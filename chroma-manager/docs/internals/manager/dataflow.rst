
Inter process communication
===========================

Inter-process communication in Chroma happens in three ways:
 * HTTP/HTTPS
 * RPC (RabbitMQ)
 * Message queues (RabbitMQ)

Toplevel
--------

*Arrows mean 'uses' or 'calls out to'*

.. graphviz::

    digraph toplevel_dataflow {
        "chroma-manager" -> rabbitmq
        "chroma-manager" -> MySQL
        chroma_cli -> chroma_api -> "chroma-manager"
        chroma_ui -> chroma_api -> "chroma-manager"
        "third party client" -> chroma_api
        "chroma-manager" -> "chroma-agent"
    }



HTTPS handling
--------------

*Arrows mean 'sends HTTP requests to'*

.. graphviz::

    digraph https_dataflow {
            "Nginx (HTTPS)" -> http_agent [label="/agent/"]
            "Nginx (HTTPS)" -> "Nginx (chroma_api)" [label="/api/, /ui/"]
            "chroma-agent" -> "Nginx (HTTPS)" [label="client cert"]
            "Browser (chroma_ui)" -> "Nginx (HTTPS)"
    }



Agent communications
--------------------

*Arrows mean 'messages or commands are sent to'*

.. graphviz::

    digraph agent_dataflow {
            "chroma-agent" -> "Nginx (HTTPS)"
            "Nginx (HTTPS)" -> http_agent
            "Nginx (HTTPS)" -> "chroma-agent"
            http_agent -> "Nginx (HTTPS)"
            http_agent -> lustre_audit -> database
            http_agent -> plugin_runner -> database
            http_agent -> syslog -> database
            http_agent -> job_scheduler
            job_scheduler -> http_agent
            job_scheduler -> database
    }

In general the flow of information is from the agents, into the various services that process it, then
onwards into the database.  The reverse flow of data comes from control messages, either to run operations
on the storage servers, or to control the session contexts within which the updates are sent (i.e. requests
to reset a session).


UI and API
----------

*Arrows mean 'messages or commands are sent to'*

.. graphviz::

    digraph api_dataflow {
            "Browser (chroma_ui)" -> "Nginx (HTTPS)" -> "Nginx (chroma_api)"
            "Nginx (chroma_api)" -> "Nginx (HTTPS)" -> "Browser (chroma_ui)"
            "Nginx (chroma_api)" -> job_scheduler [label="Commands"]
            job_scheduler -> database [label="Writing state changes"]
            job_scheduler -> http_agent [label="Running agent operations"]
            database -> "Nginx (chroma_api)" [label="Displaying status"]
    }



All RPCs and Queues
-------------------

*Arrows mean 'calls out to or sends messages to'*

.. graphviz::

    digraph all_ipc {
       http_agent -> syslog [label="SyslogRxQueue",color=red]
       http_agent -> plugin_runner [label="AgentDaemonQueue",color=red]
       http_agent -> lustre_audit [label="LustreAgentRx",color=red]
       lustre_audit -> job_scheduler [label="NotificationQueue",color=red]
       job_scheduler -> http_agent [label="AgentTxQueue",color=red]
       http_agent -> job_scheduler [label="JobPluginRxQueue",color=red]

       plugin_runner -> http_agent [label="HttpAgentRpc",color=blue]
       job_scheduler -> http_agent [label="HttpAgentRpc",color=blue]
       "Nginx (chroma_api)" -> job_scheduler [label="JobSchedulerRpc",color=blue]
       job_scheduler -> plugin_runner [label="AgentDaemonRpcInterface",color=blue]
       job_scheduler -> plugin_runner [label="ScanDaemonRpcInterface",color=blue]
    }

The majority of RPCs are either chroma_api -> job_scheduler (initiating operations) or
outwards from job_scheduler (carrying out operations).  The exception of the plugin_runner -> http_agent
edge is for controlling the flow of messages from the agents to that service.

The majority of queues flow out from http_agent, as monitoring data is received from the
outside world.  The exception is the AgentTxQueue, which job_scheduler uses to send tasks
back to agents.
