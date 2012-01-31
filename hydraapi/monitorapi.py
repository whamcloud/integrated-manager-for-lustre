#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from requesthandler import AnonymousRequestHandler

from configure.models import ManagedHost
from django.shortcuts import get_object_or_404


class UpdateScan(AnonymousRequestHandler):
    def run(self, request, fqdn, token, update_scan, plugins):
        from hydraapi import api_log
        api_log.debug("UpdateScan %s" % fqdn)

        host = get_object_or_404(ManagedHost, fqdn = fqdn)

        if token != host.agent_token:
            api_log.error("Invalid token for host %s: %s" % (fqdn, token))
            from hydraapi.requesthandler import APIResponse
            return APIResponse({}, 403)

        if update_scan:
            from monitor.lib.lustre_audit import UpdateScan
            UpdateScan().run(host.pk, update_scan)

        # TODO: make sure UpdateScan is committing because we might fail out here
        # if we can't get to rabbitmq, but we'd like to save the updatescan info even if that
        # is the case.

        response = {'plugins': {}}
        for plugin_name, response_dict in plugins.items():
            from configure.lib.storage_plugin.messaging import PluginRequest, PluginResponse

            # If the agent returned any responses for requests to the plugin, add
            # them to server queues
            for request_id, response_data in response_dict.items():
                PluginResponse.send(plugin_name, host.fqdn, request_id, response_data)

            # If any requests have been added to server queues for this plugin, pass
            # them to the agent.
            requests = PluginRequest.receive_all(plugin_name, host.fqdn)
            response['plugins'][plugin_name] = requests

        return response


class GetJobs(AnonymousRequestHandler):
    def run(self, request):
        from configure.models import Job
        from datetime import timedelta, datetime
        from django.db.models import Q
        jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))
        return [j.to_dict() for j in jobs]
