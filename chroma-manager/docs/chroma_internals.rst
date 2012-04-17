
Chroma internals
=======================================

.. contents::

chroma-manager
--------------

chroma_core
___________

The data store and business logic.

This contains the database models used by Chroma Manager -- none of the other apps have their
own models.

In addition to the models, the core defines the logic for manipulating and monitoring the state
of the system.

To get an idea of the code involved in changing the state of a filesystem, take a look at
StatefulObject, StateChangeJob and StateManager.

chroma_ui
_________

The web interface.

The UI code is mainly Javascript.  There is a minimal amount of Python for serving the Javascript.
There is no interaction between this and other apps at the Python level, the UI only accesses
the database indirectly via the HTTP API.

Rather than Django templates, the UI is built by the Javascript code, accessing the API.

Various libraries are used, the most important are jQuery and Backbone.js.

chroma_api
__________

The REST API.

The API code depends on chroma_core for all persistence and filesystem logic.  It is a thin layer
responsible for presenting the objects in a consistent way, and mapping requests from the
client to operations in the form the core expects.

The API code uses the tastypie library, which provides sensible defaults for the most part, with
overrides where we require behaviours beyond the obvious CRUD.

Many of the Resources in chroma_api correspond to a particular model in chroma_core, but not all.
Similarly, not all of the models in chroma_core are accessible as resources in the API.

chroma_cli
__________

The command line interface.

The CLI code is a peer of the UI, also consuming the API over HTTP.

This is an entirely standalone python module (it is not a Django app).

r3d
____

A database-backed time series store, used for storing statistics.  This is only used by chroma_core.

chroma-agent
------------

The agent runs on Lustre servers, and all operations that the manager does on a server are
done on its behalf by the agent, invoked via SSH.  The agent is also responsible for periodically posting
reports back to the manager via HTTP.

chroma_agent/device_plugins
___________________________

These are modules which follow the interface in chroma_agent.plugins.DevicePlugin.

.. autoclass:: chroma_agent.plugins.DevicePlugin
  :members:

chroma_agent/action_plugins
___________________________

These are modules which follow the interface in chroma_agent.plugins.ActionPlugin.

.. autoclass:: chroma_agent.plugins.ActionPlugin
  :members:
