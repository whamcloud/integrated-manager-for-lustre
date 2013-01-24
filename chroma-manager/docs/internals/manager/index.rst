
chroma-manager
==============

.. toctree::
  :maxdepth: 2

  commands
  services
  dataflow
  job_scheduler
  plugin_runner


chroma_core
___________

The main database models and backend services.  This is where the code that defines our
schema for servers, filesystems etc lives, along with the code for communicating with
chroma-agent to drive those objects in real life.

The database schema is defined in chroma_core.models.

The backend services are defined in chroma_core.services.

Backend operations are exposed to HTTP request handlers (i.e. :ref:`chroma_api`) via RPC: for example,
when a user clicks the button to start a filesystem in the web interface, this leads to an HTTP request,
the handler of that request invokes an RPC to the relevant backend service, which really performs the
operation.


chroma_ui
_________

The web interface.

The UI code is mainly Javascript.  There is a minimal amount of Python for serving the Javascript.
There is no interaction between this and other apps at the Python level, the UI only accesses
the database indirectly via the HTTP API.

Rather than Django templates, the UI is built by the Javascript code, accessing the API.  A mixture
of ad-hoc page generation and underscore.js templates are used -- the trend is towards underscore.js
templates for all new code.

Various libraries are used, the most important are jQuery and Backbone.js.

.. _chroma_api:

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

This is a vanilla Python module, not a Django app.

r3d
____

A database-backed time series store, used for storing statistics.  This is used by chroma_core in addition
to its own models.

plugins
_______

This contains builtin plugins, principally used for generic Linux storage device
detection (in chroma_core.plugins.linux)

