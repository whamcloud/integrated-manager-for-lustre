chroma-agent
------------

The agent runs on Lustre servers, and all operations that the manager does on a server are
done on its behalf by the agent, invoked via SSH.  The agent is also responsible for periodically posting
reports back to the manager via HTTP.

device_plugins
______________

*Device plugins* are python modules which provide monitoring of

These are modules which follow the interface in chroma_agent.plugin_manager.DevicePlugin.

.. autoclass:: chroma_agent.plugin_manager.DevicePlugin
  :members:

action_plugins
_______________

These are modules which follow a simple implicit interface.  They define a 1 or more functions, and
set module-scope names ACTIONS and CAPABILITIES to a list of 1 or more functions and a list of 0
or more strings respectively.

.. automodule: chroma_agent.action_plugins
  :undoc-members: