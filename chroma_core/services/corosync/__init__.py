# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple, defaultdict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from chroma_core.models import ManagedHost, HostOfflineAlert
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import AgentRxQueue
from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_core.models import CorosyncNoPeersAlert
from chroma_core.models import StonithNotEnabledAlert
from emf_common.lib.date_time import EMFDateTime

log = log_register(__name__)


class Service(ChromaService):
    """Corosync host offline detection service

    The corosync agent will report host status for all nodes in it's
    peer group.  Any node that is down according to corosync
    will be recorded here, and in the DB, and and alert will be saved.

    Be sure to have all nodes on the exact same time - ntp.  This service will
    drop older reports that come in late, so correct timing is critical.
    """

    PLUGIN_NAME = "corosync"

    #  Class to store the in-memory online/offline status and sample times
    #  a HostStatus object is created for each host that is reported
    HostStatus = namedtuple("HostStatus", ["status", "datetime"])

    def __init__(self):
        super(Service, self).__init__()

        #  Holds each host seen as a key with a HostStatus value last set
        self._host_status = defaultdict(self.HostStatus)

        self._queue = AgentRxQueue(Service.PLUGIN_NAME)

    # Using transaction decorator to ensure that subsequent calls
    # see fresh data when polling the ManagedHost model.
    @transaction.atomic
    def on_data(self, fqdn, body):
        """Process all incoming messages from the Corosync agent plugin

        Request to have the status changed for an instance.  If the current
        state determines that a host is offline, then raise that alert.

        old messages should not be processed.

        datetime is in UTC of the node's localtime in the standard
        ISO string format
        """

        try:
            host = ManagedHost.objects.get(fqdn=fqdn)
        except ManagedHost.DoesNotExist:
            # This might happen when we are deleting a host and the queues mean a message is still sat waiting to be
            # processed. Something has spoken to us and we don't know anything about it so really we can't do anything
            # other than drop it.
            log.warning("Corosync message from unknown host %s, the message was dropped." % fqdn)
            return

        # If corosync is not configured yet, or we don't actually have corosync - then ignore the input
        if (not host.corosync_configuration) or host.corosync_configuration.state == "unconfigured":
            return

        if body.get("state"):
            job_scheduler_notify.notify(
                host.corosync_configuration, timezone.now(), {"state": body["state"]["corosync"]}
            )

            job_scheduler_notify.notify(
                host.pacemaker_configuration, timezone.now(), {"state": body["state"]["pacemaker"]}
            )

            if body["state"]["corosync"] == "stopped":
                return
        else:
            if host.corosync_configuration.state != "started":
                return

        if body.get("crm_info"):
            nodes = body["crm_info"]["nodes"]
            dt = body["crm_info"]["datetime"]

            options = body["crm_info"].get("options", {"stonith_enabled": None})
            stonith_enabled = options["stonith_enabled"]

            try:
                dt = EMFDateTime.parse(dt)
            except ValueError:
                if dt != "":
                    log.warning("Invalid date or tz string from corosync plugin: %s" % dt)
                    raise

            def is_new(peer_node_identifier):
                return (
                    peer_node_identifier not in self._host_status
                    or self._host_status[peer_node_identifier].datetime < dt
                )

            peers_str = "; ".join(
                [
                    "%s: online=%s, new=%s" % (peer_node_identifier, data["online"], is_new(peer_node_identifier))
                    for peer_node_identifier, data in nodes.items()
                ]
            )
            log.debug("Incoming peer report from %s:  %s" % (fqdn, peers_str))

            # NB: This will ignore any unknown peers in the report.
            cluster_nodes = ManagedHost.objects.prefetch_related("ha_cluster_peers").filter(
                Q(nodename__in=nodes.keys()) | Q(fqdn__in=nodes.keys())
            )

            unknown_nodes = (
                set(nodes.keys()) - set([h.nodename for h in cluster_nodes]) - set([h.fqdn for h in cluster_nodes])
            )

            # Leaving this out for now - because they raise issue caused by limitations in the simulator and
            # test system as a whole. Difficult to know if they will or won't be raised it all depends on the past.
            # CorosyncUnknownPeersAlert.notify(host.corosync_configuration, unknown_nodes != set())
            if unknown_nodes:
                log.warning("Unknown nodes in report from %s: %s" % (fqdn, unknown_nodes))

            if stonith_enabled is not None:
                StonithNotEnabledAlert.notify(host.corosync_configuration, stonith_enabled is False)

            CorosyncNoPeersAlert.notify(host.corosync_configuration, len(cluster_nodes) == 1)
            # CorosyncToManyPeersAlert.notify(host.corosync_configuration, len(cluster_nodes) > 2)

            #  Consider all nodes in the peer group for this reporting agent
            for host in cluster_nodes:
                try:
                    data = nodes[host.nodename]
                    node_identifier = host.nodename
                except KeyError:
                    data = nodes[host.fqdn]
                    node_identifier = host.fqdn

                cluster_peer_keys = sorted([node.pk for node in cluster_nodes if node is not host])

                if is_new(node_identifier) and host.corosync_configuration:
                    host_reported_online = data["online"] == "true"

                    log.debug("Corosync processing " "peer %s of %s " % (host.fqdn, fqdn))

                    #  Raise an Alert - system suppresses duplicates
                    log.debug("Alert notify on %s: active=%s" % (host, not host_reported_online))
                    HostOfflineAlert.notify(host, not host_reported_online)
                    if host_reported_online == False:
                        log.debug("Host %s offline" % host.fqdn)
                    else:
                        log.debug("Host %s online" % host.fqdn)

                    #  Attempt to save the state.
                    if host.corosync_configuration.corosync_reported_up != host_reported_online:
                        job_scheduler_notify.notify(
                            host.corosync_configuration, timezone.now(), {"corosync_reported_up": host_reported_online}
                        )

                    peer_host_peer_keys = sorted([h.pk for h in host.ha_cluster_peers.all()])
                    if peer_host_peer_keys != cluster_peer_keys:
                        job_scheduler_notify.notify(host, timezone.now(), {"ha_cluster_peers": cluster_peer_keys})

                    #  Keep internal track of the hosts state.
                    self._host_status[node_identifier] = self.HostStatus(status=host_reported_online, datetime=dt)

    def run(self):
        super(Service, self).run()

        self._queue.serve(data_callback=self.on_data)

    def stop(self):
        super(Service, self).stop()

        self._queue.stop()
