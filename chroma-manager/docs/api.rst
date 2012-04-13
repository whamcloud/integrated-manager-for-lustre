
Chroma REST API
===============

Introduction
------------

The Chroma web interface and command line are built on an API, accessed
via HTTP.  This API is available for integration with third party applications.  The 
types of operations possible using the API include creating a filesystem, checking
the system for alert conditions and downloading performance metrics.  All functionality
provided in the standard Chroma web interface is based on this API, so anything that
the web interface can do is also possible for third party applications.

The API is based on the `REST <http://en.wikipedia.org/wiki/Representational_state_transfer>`_
style, and uses `JSON <http://en.wikipedia.org/wiki/JSON>`_ serialization.  Some of the
resources exposed in the API correspond to things within the Lustre filesystem, while
others refer to Chroma-specific functionality.

This document consists of a series of sections explaining how to use the API, followed
by an `Example client`_, and a detailed `API Reference`_ describing all
available functionality.

Prerequisites
~~~~~~~~~~~~~

* Familiarity with managing Lustre using Chroma server's web interface.
* Familiarity with HTTP, including the meanings and conventions around the 
  methods (e.g. GET, POST, DELETE) and status codes (e.g. 404, 200).
* Competance in a suitable high level programming language to write your
  API client, and the libraries used with your language for HTTP network
  operations and JSON serialization.

Overview of Lustre filesystems in the API
-----------------------------------------

Terminology
~~~~~~~~~~~

We avoid some of the redundant terminology from manual Lustre 
adminitration.  Especially, we avoid referring to hosts as 
OSS, MDS or MGS -- this terminology is ambiguous as a host can
serve targets of different types.  The Lustre specific terminology
used in the API is:

:OST: a block device formatted as an object store target
:MDT: a block device formatted as a metadata target
:MGT: a block device formatted as a management target
:Filesystem: a collection of MGT, MDTs and OSTs

Objects and relationships
~~~~~~~~~~~~~~~~~~~~~~~~~

The following objects are required for a running filesystem:
MGT, MDT, OST (`Targets <#target>`_), `Filesystem <#filesystem>`_,
`Volume <#volume>`_, `Volume node <#volume_node>`_, `Host <#host>`_.

The order of construction permitted for API consumers is:

1. Hosts
2. Volumes and volume nodes (these are detected from hosts)
3. MGTs (these may also be created during filesystem creation)
4. Filesystem (includes creating an MDT and one or most OSTs)
5. Any additional OSTs (added to an existing filesystem)

The following cardinality rules are observed:

* An MGT has zero or more filesystems, each filesystem belongs to one MGT.
* A filesystem has one or more MDTs, each MDT belongs to one filesystem.
  *(exception: a filesystem which is in the process of being deleted passes
  through a stage where it has zero MDTs)*
* A filesystem has one or most OSTs, each OST belongs to one filesystem.
  *(exception: a filesystem which is in the process of being deleted passes
  through a stage where it has zero OSTs)*
* MDTs, MGTs and OSTs are Targets.  Targets are associated with one or more
  primary Volume nodes, and zero or more secondary volume nodes.  Targets
  are associated with exactly one Volume, and each volume is associated with
  zero or one targets.
* Volume nodes are associated with zero or one targets, exactly one volume,
  and exactly one host.


Fetching objects
----------------

Access to objects such as servers, targets and filesystems is provided via meaningful URLs, for
example access a filesystem with ID 1, we would use ``/api/filesystem/1/``.  To read its attributes
we would use an HTTP GET operation, while to modify them we would send back a modified copy
of the object using an HTTP PUT operation to the same URL.  The PUT verb tells the server
that you want to modify something, the URL tells the server which object you want to modify,
and the payload contains the updated fields.  Operations using a URL for a specific object
are referred to in this document as _detail_ operations.  These operations usually
return a single serialized object in the response.

To see all the filesystems, we simply leave the /1/ off the URL and do a ``GET /api/filesystem/``.
This type of operation is referred to in this document as a _list_ operation. 

Filtering and ordering
~~~~~~~~~~~~~~~~~~~~~~

To filter on an attribute value, pass it as an argument to a GET request.  For example,
to get targets belonging to a filesystem with ID 1, ``GET /api/target/?filesystem_id=1``

Ordering of results is done using the ``order_by`` URL parameter, set to the name
of the attribute to order by, prefixed with ``-`` to reverse the order.  For example, 
to get all targets in reverse name order, the URL would be ``/api/target/?order_by=-name``.

More advanced filtering is also possible (Note: Chroma server uses the Django framework
to access its database, and these are `'django style' queries <https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups>`_).  These use double-underscore
suffixes to field names to indicate the type of filtering, some of the commonly used filters
are in the following list:

:__in: Has one of the values in a list
:__lt: Less than
:__gt: Greater than
:__lte: Less than or equal to
:__gte: Greater than or equal to
:__contains: Contains the string (case sensitive)
:__icontains: Contains the string (case insensitive)
:__startswith: Starts with the string
:__endswith: Ends with the string

For example, if an object supports ``id__in`` filtering,
this represents an "If its ID is in this list" query.  Note that passing lists as URL 
parameters is done by repeating the argument, so to get a list of targets 1 and 2, the
URL would be ``/api/target/?id__in=1&id__in=2``.  

See the `API Reference` for details of which attributes are permitted for ordering and
filtering on a resource-by-resource basis.


Encoding
~~~~~~~~

The API will respect the ``Accept`` header in your request.  Set this to ``application/json``
to receive JSON responses.

JSON does not define an encoding for dates and times: the Chroma API uses the `ISO8601 <http://www.w3.org/TR/NOTE-datetime>`_ format for dates and times, with the caveat that the timezone must
be specified in values, or behaviour is undefined.

You may find it useful to browse the API using a web browser.  To do this on a running
system, first log into the Chroma web interface, and then point your browser at
``http://my-chroma-manager/api/host/?format=json``.  The resulting output is best browsed
using a plugin like ``JSONView`` for Google Chrome.  Note that using ``format=json`` is
only necessary when using a browser: your own client will set the ``Accept`` header instead.

Detail responses
~~~~~~~~~~~~~~~~

Detail GET requests (e.g. ``GET /api/host/1/``) return a dict representing a single object.

Most serialized objects have at least ``resource_uri`` and ``id`` field.  Where an object 
has a 'human' name that is useful for presentation, this is called ``label``.

Note that in some cases it may be necessary to manually compose the URL for an object
based on its type and integer ID, usually when an object is provided by the server it
is accompanied by a ``resource_uri`` attribute which should be used for subsequent
access to the object instead of building the URL on the client.


List responses
~~~~~~~~~~~~~~

All list methods (e.g. ``GET /api/host``) return a dict with 'meta' and 'objects' keys.  The
'meta' key contains information about the set of objects returned, which is useful for
pagination.

If you wish to obtain all objects, pass ``limit=0`` as a parameter to the request.

.. code-block:: javascript


    {
        "meta": {
            "limit": 20,
            "next": null,
            "offset": 0,
            "previous": null,
            "total_count": 2
        },
        "objects": [{...}, {...}]
    }

:``limit``: the max. number of records returned in each response (you may pass this
            as a parameter to your request, or pass 0 to fetch an unlimited number)
:``offset``: offset of this page into the overall result (you may pass this as a parameter
             to your request)
:``total_count``: the total number of records matching your request, before pagination
:``next``: a URL to the next page of results
:``previous``: a URL to the previous page of results


Creating, modifying and deleting objects
----------------------------------------

Objects are created using the POST method.  The attributes provided at creation
time are sent as a JSON-encoded dict in the body of the POST (*not* as URL
parameters).  If an object is successfully created, its identifier will
be included in the response.

Some resources support the PUT method to modify them.  In some cases, this
may be a literal immediate modification of an attribute (such as altering
a human readable name), while in other cases this will start an asynchronous
operation (such as changing the ``state`` attribute of a target from ``mounted``
to ``unmounted``).  Most attributes are read only: where it is possible to use
PUT to modify a resource, this is stated in the resource's documentation (see
`API Reference`_

On resources which support the DELETE method, this may be used to remove them
from the chroma server.  Some objects can always be removed immediately, while
others take some time to remove and the operation may not succeed.  For example,
removing a filesystem requires removing the configuration of its targets from
the Lustre servers: if a DELETE is sent for such an object then the operation
will be run asynchronously (see `Asynchronous actions`_)

Asynchronous actions
~~~~~~~~~~~~~~~~~~~~

Where an action will occur in the background, the ACCEPTED (202) status code is
returned, with a dictionary containing a command object, e.g.:

.. code-block:: javascript


    {
        "command": {
            "id": 22,
            "resource_uri": 22,
            "message": "Starting filesystem testfs"
        }
    }

In some cases the response may include additional fields describing work
that was completed synchronously: for example, POSTing to ``/api/filesystem/``
returns the ``command`` for setting up a filesystem, and also the newly
created ``filesystem``.

You can poll the ``/api/command/<command-id>/`` resource to check the 
status of your asynchronous operation.  You may start multiple operations
and allow them to run in parallel.

State changes
~~~~~~~~~~~~~

Some objects with a ``state`` attribute allow PUTs to modify this, and return a
command for the resulting action.  To determine valid values for the state, examine
the ``available_transitions`` attribute of the object: this is a list of objects,
each with a ``state`` attribute and a ``verb`` attribute.  The ``verb`` attribute
is a hint for presentation to the user, while the ``state`` attribute is what should
be written back to the original object's ``state`` field in a PUT to cause its
state to change.

For example, consider this host object:

.. code-block:: javascript

    {
        address: "flint02",
        available_transitions: [
            {
                state: "removed",
                verb: "Remove"
            },
            {
                state: "lnet_unloaded",
                verb: "Unload LNet"
            },
            {
                state: "lnet_down",
                verb: "Stop LNet"
            }
        ],
        content_type_id: 6,
        fqdn: "flint02",
        id: "10",
        label: "flint02",
        last_contact: "2012-02-14T20:52:41",
        nodename: "flint02",
        resource_uri: "/api/host/10/",
        state: "lnet_up"
    }


The host is in state ``lnet_up``.  To stop LNet (as indicated by the 'lnet_down'/'Stop LNet' 
transition in available transitions) we would PUT ``{"state": "lnet_down"}`` to ``/api/host/10/``.

Assuming the transition sent is a valid one, this PUT would response with status code 204,
and would include a ``command`` in the response (see `Asynchronous actions`_)

Access control
--------------

If your application requires write access to the Chroma server, or if the server
is configured to prevent anonymous users from reading, then your application must
authenticate itself to the server.

User accounts and credentials can be created and managed using the Chroma web
interface -- we assume here that a suitable account has already been created.  Create
an account for your application with the lowest possible privilege level.

For a complete example of how to authenticate with a Chroma server, see the `Example client`_.

Sessions
~~~~~~~~

Only applies when authenticating by username and password.

Before authenticating you must establish a session.  Do this by sending
a GET to ``/api/session/``, and including the returned ``sessionid`` cookie
in subsequent responses.

CSRF
~~~~

Only applies when authenticating by username and password.

Because the API is accessed directly from a web browser, it requires CSRF
protection.  If you do not know what CSRF is, then don't worry.  The 
effect on API consumers is that when authenticating by username+password,
you must accept and maintain the ``csrftoken`` cookie, which is returned
from the same ``/api/session/`` resource used to establish a session, and additionally
set the X-CSRFToken request header to the value of that cookie.

Note that an absent or incorrect CSRF token only causes an error on POST requests.


Authentication
~~~~~~~~~~~~~~

**By username and password**
  Once a session is established, you may authenticate by POSTing to ``/api/session``
  (see `session <#session-api-session>`_).

**By key**
  *Currently, API consumers must log in using the same username/password credentials
  used in the web interface.  This will be augmented with optional public key authentication
  in future versions.  API consumers authenticating using a key will be exempt from the 
  need to maintain a session and handle CSRF tokens.*



Validation and error handling
-----------------------------

Invalid requests
~~~~~~~~~~~~~~~~

BAD REQUEST (400) responses to POSTs or PUTs may be intepreted as validation errors
on the fields submitted.  The response body will contain a dictionary of
field names to error messages, which can be presented to the user as validation
errors on the fields.

For example, attempting to create a filesystem with a name longer than 8 characters
might give a 400 response with the following body:

.. code-block:: javascript


    {
        "name": "Filesystem name 'verylongname' is too long (limit 8 characters)"
    }

BAD REQUEST (400) responses to GETs and DELETEs indicate that something more
serious was wrong with the request, for example the caller attempted to filter
or sort on a field that is not permitted.

Exceptions
~~~~~~~~~~

INTERNAL SERVER ERROR (500) If an unhandled exception occurs during an API call, if Chroma server is running
in development mode, the exception and traceback will be serialized and returned as JSON:

.. code-block:: javascript

    {
        "error_message": "Exception 'foo'",
        "traceback": "Traceback (most recent call last):\n  File "/usr/lib/python2.7/site-packages/django/core/handlers/base.py", line 111, in get_response\n    response = callback(request, *callback_args, **callback_kwargs)"
    }




Example client
--------------

The example below is written in Python and uses the excellent ``python-requests``
module for HTTP operations.  It demonstrates how to establish a session, authenticate,
and retrieve a list of hosts.

.. literalinclude:: example_api_client.py
   :language: python
   :linenos:

API Reference
-------------

Note: in addition to the information in this document, you may inspect the 
available API resources and their fields on a running Chroma server.  Enumerate 
available resources by GETing ``/api/``.  The resulting list includes links to 
individual resource schemas like ``/api/host/schema``.

.. tastydoc:: chroma_api.urls.api
