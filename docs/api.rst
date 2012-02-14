
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

This document consists of a series of sections explaining how to use the API, followed
by an `Example client`_, and a detailed `API reference`_ of all
available functionality.

Prerequisites
~~~~~~~~~~~~~

* Familiarity with managing Lustre using Chroma server's web interface.
* Familiarity with HTTP, including the meanings and conventions around the 
  methods (e.g. GET, POST, DELETE) and status codes (e.g. 404, 200).
* Competance in a suitable high level programming language to write your
  API client, and the libraries used with your language for HTTP network
  operations and JSON serialization.

Fetching objects
----------------

Access to objects such as servers, targets and filesystems is provided via meaningful URLs, for
example access a filesystem with ID 1, we would use /api/filesystem/1/.  To read its attributes
we would use an HTTP GET operation, while to modify them we would send back a modified copy
of the object using an HTTP PUT operation to the same URL.  The PUT verb tells the server
that you want to modify something, the URL tells the server which object you want to modify,
and the payload contains the updated fields.  Operations using a URL for a specific object
are referred to in this document as _detail_ operations.  These operations usually
return a single serialized object in the response.

To see all the filesystems, we simply leave the /1/ off the URL and do a "GET /api/filesystem/".
This type of operation is referred to in this document as a _list_ operation. 

Encoding
~~~~~~~~

We recommend that clients use JSON when dealing with the API.  XML can be used instead,
but it provides no additional meaning compared with JSON, and is harder to read and debug.

The API will respect the ``Accept`` header in your request.  Set this to ``application/json``
to receive JSON responses.

You may find it useful to browse the API using a web browser.  To do this on a running
system, first log into the Chroma web interface, and then point your browser at
http://my-chroma-server/api/host/?format=json.  The resulting output is best browsed
using a plugin like ``JSONView`` for Google Chrome.


Detail responses
~~~~~~~~~~~~~~~~

All detail methods (e.g. GET /api/host/1/) return a dict representing a single object.

Most serialized objects have at least ``resource_uri`` and ``id`` field.

Where an object has a 'human' name that is useful for presentation, this is called ``label``.


List responses
~~~~~~~~~~~~~~

All list methods (e.g. GET /api/host) return a dict with 'meta' and 'objects' keys.  The
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
a GET to /api/session/, and including the returned ``sessionid`` cookie
in subsequent responses.

CSRF
~~~~

Only applies when authenticating by username and password.

Because the API is accessed directly from a web browser, it requires CSRF
protection.  If you do not know what CSRF is, then don't worry.  The 
effect on API consumers is that when authenticating by username+password,
you must accept and maintain the ``csrftoken`` cookie, which is returned
from the same /api/session/ resource used to establish a session, and additionally
set the X-CSRFToken request header to the value of that cookie.

Note that an absent or incorrect CSRF token only causes an error on POST requests.


Authentication
~~~~~~~~~~~~~~

By username and password
________________________

Once a session is established, you may authenticate by POSTing to ``/api/session``
(see api-session_).

By key
______

Currently, API consumers must log in using the same username/password credentials
used in the web interface.  This will be augmented with optional public key authentication
in future versions.  API consumers authenticating using a key will be exempt from the 
need to maintain a session and handle CSRF tokens.



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
        "traceback": "Traceback (most recent call last):\n  File "/Users/jcspray/hydra/lib/python2.7/site-packages/django/core/handlers/base.py", line 111, in get_response\n    response = callback(request, *callback_args, **callback_kwargs)"
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

.. tastydoc:: urls.api
