
# The code below changes the behaviour of AgentPluginHandler.setup_host so that
# it works in the context of the mocking that takes place in the Selenium tests.
#
# It is required as part of HYD-3068. HYD-3068 enforced the fact that all communications
# with the plugins must take place within the context of a session. This is good
# practice to ensure that data integrity is preserved in all situtations.
#
# However the mocking used for Selenium tests doesn't create sessions and so the
# new implementation of AgentPluginHandler.setup_host would fail with an assertion.
# The code below is the pre-HYD-3068 code that creates a one off plugin and connection
# for the specific purpose of fetching the initial data from the agent plugin.
#
# The plan is for the mocking method for Selenium to change and so with a bit of
# luck and a following breeze this awful mock will disappear soon.
#
# For now using the old code to test the front end is an acceptable compromise


def setup_host_for_selenium_tests(self, host_id, data):
    from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

    with self._processing_lock:
        host = ManagedHost.objects.get(id = host_id)

        try:
            record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                plugin_name = self._plugin_name, host_id = host.id)
        except StorageResourceRecord.DoesNotExist:
            log.info("Set up plugin %s on host %s" % (self._plugin_name, host))
            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
            record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': self._plugin_name, 'host_id': host.id})

        if data is not None:
            instance = self._plugin_klass(self._resource_manager, record.id)
            instance.do_agent_session_start(data)


AgentPluginHandler.setup_host = setup_host_for_selenium_tests
