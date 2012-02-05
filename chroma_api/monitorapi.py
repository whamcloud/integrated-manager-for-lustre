#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_api.requesthandler import RequestHandler

from chroma_core.models import ManagedHost
from django.shortcuts import get_object_or_404

from chroma_api import api_log



class UpdateScan(RequestHandler):
    def post(self, request, fqdn, token, update_scan, plugins):
        api_log.debug("UpdateScan %s" % fqdn)

        host = get_object_or_404(ManagedHost, fqdn = fqdn)

        if token != host.agent_token:
            api_log.error("Invalid token for host %s: %s" % (fqdn, token))
            from chroma_api.requesthandler import APIResponse
            return APIResponse({}, 403)

        if update_scan:
            from chroma_core.lib.lustre_audit import UpdateScan
            UpdateScan().run(host.pk, update_scan)

        # TODO: make sure UpdateScan is committing because we might fail out here
        # if we can't get to rabbitmq, but we'd like to save the updatescan info even if that
        # is the case.

        response = {'plugins': {}}
        for plugin_name, response_dict in plugins.items():
            from chroma_core.lib.storage_plugin.messaging import PluginRequest, PluginResponse

            # If the agent returned any responses for requests to the plugin, add
            # them to server queues
            for request_id, response_data in response_dict.items():
                PluginResponse.send(plugin_name, host.fqdn, request_id, response_data)

            # If any requests have been added to server queues for this plugin, pass
            # them to the agent.
            requests = PluginRequest.receive_all(plugin_name, host.fqdn)
            response['plugins'][plugin_name] = requests

        return response
