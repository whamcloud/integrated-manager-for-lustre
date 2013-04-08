
.. include:: <isonum.txt>

REST API for Intel\ |reg| Manager for Lustre* Software
======================================================

Introduction
------------

The Command Center web interface and command line interface (CLI) included with the 
Intel\ |reg| Manager for Lustre* software are built on the REST API, which is accessed
via HTTP.  This API is available for integration with third party applications.  The 
types of operations possible using the API include creating a file system, checking
the system for alert conditions, and downloading performance metrics.  All functionality
provided in the Command Center web interface is based on this API, so anything 
that can be done using the web interface can also potentially be done from third party 
applications.

The API is based on the `REST <http://en.wikipedia.org/wiki/Representational_state_transfer>`_
style, and uses `JSON <http://en.wikipedia.org/wiki/JSON>`_ serialization.  Some of the
resources exposed in the API correspond to functionality within the Lustre file system, while
others refer to functionality specific to the Intel Manager for Lustre software.

This document consists of a series of sections explaining how to use the API, followed
by an `Example client`_, and a detailed `API Reference`_ describing all
available functionality.

Prerequisites
~~~~~~~~~~~~~

* Familiarity with managing Lustre using the Command Center web interface provided 
  with the Intel Manager for Lustre software.
* Familiarity with HTTP, including the meanings and conventions around the 
  methods (e.g. GET, POST, DELETE) and status codes (e.g. 404, 200).
* Competence in using a suitable high level programming language to write your
  API client and the libraries used with your language for HTTP network
  operations and JSON serialization.

Overview of Lustre File Systems in the API
------------------------------------------

Terminology
~~~~~~~~~~~

The terminology used in this document differs somewhat from that used when administering a 
Lustre file system manually. This document avoids referring to a host as an object storage server (OSS), 
metdata server (MDS), or management server (MGS) because, in a Lustre file system created using the 
Intel Manager for Lustre software, a host can serve targets of any of these types.
 
Lustre-specific terms used in this API include:

:OST: a block device formatted as an object store target
:MDT: a block device formatted as a metadata target
:MGT: a block device formatted as a management target
:File system: a collection of MGT, MDTs and OSTs

Objects and Relationships
~~~~~~~~~~~~~~~~~~~~~~~~~

The following objects are required for a running file system:
MGT, MDT, OST (`target <#target>`_), `filesystem <#filesystem>`_,
`volume <#volume>`_, `volume node <#volume-node>`_, `host <#host>`_.

The order of construction permitted for consumers of the REST API is:

1. Hosts
2. Volumes and volume nodes (these are detected from hosts)
3. MGTs (these may also be created during file system creation)
4. File system (includes creating an MDT and one or more OSTs)
5. Any additional OSTs (added to an existing file system)

The following cardinality rules are observed:

* An MGT has zero or more file systems, each file system belongs to one MGT.
* A file system has one or more MDTs, each MDT belongs to one file system.
  *(exception: a file system that is in the process of being deleted passes
  through a stage where it has zero MDTs)*
* A file system has one or most OSTs, each OST belongs to one file system.
  *(exception: a file system that is in the process of being deleted passes
  through a stage where it has zero OSTs)*
* MDTs, MGTs and OSTs are targets.  Targets are associated with one
  primary volume node, and zero or more secondary volume nodes.  Targets
  are associated with exactly one volume, and each volume is associated with
  zero or one targets.
* Volume nodes are associated with zero or one targets, exactly one volume,
  and exactly one host.


Fetching Objects
----------------

Access to objects such as servers, targets and file systems is provided using meaningful URLs. For
example, to access a file system with ID 1, use ``/api/filesystem/1/``.  To read file system attributes,
use an HTTP GET operation, while to modify the attributes, send back a modified copy
of the object using an HTTP PUT operation to the same URL.  The PUT verb tells the server
that you want to modify something, the URL tells the server which object you want to modify,
and the payload contains the updated fields.  

Operations using a URL for a specific object are referred to in this document as _detail_ operations.
These operations usually return a single serialized object in the response.

To see all the file systems, omit the /1/ in the URL and do a ``GET /api/filesystem/``.
This type of operation is referred to in this document as a _list_ operation. 

Use of HTTPS
~~~~~~~~~~~~

By default, Chroma manager uses a server certificate signed by its built-in CA.  To verify this
certificate in an API client, you must download the Chroma manager CA.  The CA is available for
download from the manager server at the ``/certificate/`` path.

Filtering and Ordering
~~~~~~~~~~~~~~~~~~~~~~

To filter on an attribute value, pass the attribute and value as an argument to a GET request.  For example,
to get targets belonging to a file system with ID 1, use ``GET /api/target/?filesystem_id=1``

Ordering of results is done using the ``order_by`` URL parameter set to the name
of the attribute by which the results are to be ordered, prefixed with ``-`` to reverse the order.  For example, 
to get all targets in reverse name order, use the URL ``/api/target/?order_by=-name``.

More advanced filtering is also possible (Note: The Command Center server uses the Django``*`` framework
to access its database, so `'django style' queries <https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups>`_ are used).  They use double-underscore
suffixes to field names to indicate the type of filtering. Some commonly used filters
are shown in the following list:

:__in: Has one of the values in a list
:__lt: Less than
:__gt: Greater than
:__lte: Less than or equal to
:__gte: Greater than or equal to
:__contains: Contains the string (case sensitive)
:__icontains: Contains the string (case insensitive)
:__startswith: Starts with the string
:__endswith: Ends with the string

For example, an object that supports ``id__in`` filtering allows an "If its ID is in this list" query.  Note that 
to pass lists as URL parameters, the argument must be repeated. So, to get a list of targets 1 and 2, the
URL is ``/api/target/?id__in=1&id__in=2``.  

See the `API Reference`_ for details about which attributes are permitted for ordering and
filtering on a resource-by-resource basis.


Encoding
~~~~~~~~

The API will respect the ``Accept`` header in a request.  Set the Accept header to ``application/json``
to receive JSON responses.

JSON does not define an encoding for dates and times. The API uses the `ISO8601 <http://www.w3.org/TR/NOTE-datetime>`_ format 
for dates and times, with the caveat that the timezone must be specified in values or behaviour is undefined.

You may find it useful to browse the API using a web browser.  To do this on a running
system, first log into the Command Center web interface, and then point your browser at
``http://my-chroma-manager/api/host/?format=json``.  The resulting output is best browsed
using a plugin like ``JSONView`` for the Google``*`` Chrome``*`` browser.  Note that using ``format=json`` is
only necessary when using a browser: your own client will set the ``Accept`` header instead.

Detail Responses
~~~~~~~~~~~~~~~~

Detail GET requests (e.g. ``GET /api/host/1/``) return a dict representing a single object.

Most serialized objects have at least ``resource_uri`` and ``id`` fields.  Where an object 
has a human readable name that is useful for presentation, it is in an attribute called ``label``.

Note that in some cases it may be necessary to manually compose the URL for an object
based on its type and integer ID. Usually when an object is provided by the server, it
is accompanied by a ``resource_uri`` attribute which should be used for subsequent
access to the object instead of building the URL on the client.


List Responses
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

:``limit``: the maximum number of records returned in each response (you may pass this
            as a parameter to your request, or pass 0 to fetch an unlimited number)
:``offset``: offset of this page into the overall result (you may pass this as a parameter
             to your request)
:``total_count``: the total number of records matching your request, before pagination
:``next``: a URL to the next page of results
:``previous``: a URL to the previous page of results


Creating, Modifying, and Deleting Objects
-----------------------------------------

Objects are created using the POST method.  The attributes provided at creation
time are sent as a JSON-encoded dict in the body of the POST (*not* as URL
parameters).  If an object is successfully created, its identifier will
be included in the response.

Some resources support using the PUT method to modify attributes.  In some cases, executing a PUT
may result in a literal, immediate modification of an attribute (such as altering
a human readable name), while in other cases, it will start an asynchronous
operation (such as changing the ``state`` attribute of a target from ``mounted``
to ``unmounted``).  Most attributes are read only. Where it is possible to use
PUT to modify a resource, this is stated in the resource's documentation (see
`API Reference`_)

On resources that support the DELETE method, this method may be used to remove resources
from the storage server.  Some objects can always be removed immediately, while
others take some time to remove and the operation may not succeed.  For example,
removing a file system requires removing the configuration of its targets from
the Lustre servers: if a DELETE is sent for such an object then the operation
will be run asynchronously (see `Asynchronous Actions`_)

Asynchronous Actions
~~~~~~~~~~~~~~~~~~~~

When an action will occur in the background, the ACCEPTED (202) status code is
returned, with a dictionary containing a command object, e.g.:

.. code-block:: javascript


    {
        "command": {
            "id": 22,
            "resource_uri": 22,
            "message": "Starting filesystem testfs"
        }
    }

In some cases, the response may include additional fields describing work
that was completed synchronously. For example, POSTing to ``/api/filesystem/``
returns the ``command`` for setting up a file system, and also the newly
created ``filesystem``.

You can poll the ``/api/command/<command-id>/`` resource to check the 
status of your asynchronous operation.  You may start multiple operations
and allow them to run in parallel.

State Changes
~~~~~~~~~~~~~

Some objects with a ``state`` attribute allow PUTs to modify the attribute and return a
command for the resulting action.  To determine valid values for the state, examine
the ``available_transitions`` attribute of the object. This is a list of objects,
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


The host is in state ``lnet_up``.  To stop LNet, the host state can be transitioned to the appropriate available 
transition 'lnet_down'/'Stop LNet' by executing a PUT ``{"state": "lnet_down"}`` to ``/api/host/10/``.

Assuming the transition sent is a valid one, this PUT will result in a response with status code 202,
and a ``command`` will be included in the response (see `Asynchronous actions`_)

Access Control
--------------

If your application requires write access (methods other than GET) to the API, or if the server
is configured to prevent anonymous users from reading, then your application must
authenticate itself to the server.

User accounts and credentials can be created and managed using the Command Center web
interface -- we assume here that a suitable account has already been created.  Create
an account for your application with the lowest possible privilege level.

For a complete example of how to authenticate with the API, see the `Example client`_.

Sessions
~~~~~~~~

Establishing a session only applies when authenticating by username and password.

Before authenticating you must establish a session.  Do this by sending
a GET to ``/api/session/``, and including the returned ``sessionid`` cookie
in subsequent responses.

CSRF
~~~~

Cross Site Request Forgery (CSRF) protection only applies when authenticating by username and password.

Because the API is accessed directly from a web browser, it requires CSRF
protection.  When authenticating by username+password,
the client must accept and maintain the ``csrftoken`` cookie that is returned
from the  ``/api/session/`` resource used to establish the session and 
set the X-CSRFToken request header in each request to the value of that cookie.

Note that an absent or incorrect CSRF token only causes an error on POST requests.


Authentication
~~~~~~~~~~~~~~

**By username and password**
  Once a session is established, you may authenticate by POSTing to ``/api/session``
  (see `session <#session-api-session>`_).

**By key**
  *Currently, consumers of the API must log in using the same username/password credentials
  used in the web interface.  This will be augmented with optional public key authentication
  in future versions.  Authenticating using a key is exempt from the 
  requirement to maintain a session and handle CSRF tokens.*

  

Validation and Error Handling
-----------------------------

Invalid Requests
~~~~~~~~~~~~~~~~

BAD REQUEST (400) responses to POSTs or PUTs may be interpreted as validation errors
resulting from errors in fields submitted.  The body of the response contains a dictionary of
field names with corresponding error messages, which can be presented to the user as validation
errors on the fields.

For example, attempting to create a file system with a name longer than 8 characters
may result in a 400 response with the following body:

.. code-block:: javascript


    {
        "name": "Filesystem name 'verylongname' is too long (limit 8 characters)"
    }

BAD REQUEST (400) responses to GETs and DELETEs indicate that something more
serious was wrong with the request, for example, the caller attempted to filter
or sort on a field that is not permitted.

Exceptions
~~~~~~~~~~

If an unhandled exception, INTERNAL SERVER ERROR (500), occurs during an API call, and the 
Command Center is running in development mode, the exception and traceback will be serialized and returned as JSON:

.. code-block:: javascript

    {
        "error_message": "Exception 'foo'",
        "traceback": "Traceback (most recent call last):\n  File "/usr/lib/python2.7/site-packages/django/core/handlers/base.py", line 111, in get_response\n    response = callback(request, *callback_args, **callback_kwargs)"
    }


Example Client
--------------

The example below is written in Python``*`` and uses the ``python-requests``
module for HTTP operations.  It demonstrates how to establish a session, authenticate,
and retrieve a list of hosts.

.. literalinclude:: /../../tests/integration/shared_storage_configuration/example_api_client.py
   :language: python
   :linenos:

API Reference
-------------

Note: in addition to the information in this document, you may inspect the 
available API resources and their fields on a running Command Center server.  To enumerate 
available resources, use GET ``/api/``.  The resulting list includes links to 
individual resource schemas like ``/api/host/schema``.

.. tastydoc:: chroma_api.urls.api


Legal Information
-----------------

INFORMATION IN THIS DOCUMENT IS PROVIDED IN CONNECTION WITH INTEL PRODUCTS.  NO LICENSE, EXPRESS OR IMPLIED, BY ESTOPPEL OR OTHERWISE, TO ANY INTELLECTUAL PROPERTY RIGHTS IS GRANTED BY THIS DOCUMENT.  EXCEPT AS PROVIDED IN INTEL'S TERMS AND CONDITIONS OF SALE FOR SUCH PRODUCTS, INTEL ASSUMES NO LIABILITY WHATSOEVER AND INTEL DISCLAIMS ANY EXPRESS OR IMPLIED WARRANTY, RELATING TO SALE AND/OR USE OF INTEL PRODUCTS INCLUDING LIABILITY OR WARRANTIES RELATING TO FITNESS FOR A PARTICULAR PURPOSE, MERCHANTABILITY, OR INFRINGEMENT OF ANY PATENT, COPYRIGHT OR OTHER INTELLECTUAL PROPERTY RIGHT.

A "Mission Critical Application" is any application in which failure of the Intel Product could result, directly or indirectly, in personal injury or death.  SHOULD YOU PURCHASE OR USE INTEL'S PRODUCTS FOR ANY SUCH MISSION CRITICAL APPLICATION, YOU SHALL INDEMNIFY AND HOLD INTEL AND ITS SUBSIDIARIES, SUBCONTRACTORS AND AFFILIATES, AND THE DIRECTORS, OFFICERS, AND EMPLOYEES OF EACH, HARMLESS AGAINST ALL CLAIMS COSTS, DAMAGES, AND EXPENSES AND REASONABLE ATTORNEYS' FEES ARISING OUT OF, DIRECTLY OR INDIRECTLY, ANY CLAIM OF PRODUCT LIABILITY, PERSONAL INJURY, OR DEATH ARISING IN ANY WAY OUT OF SUCH MISSION CRITICAL APPLICATION, WHETHER OR NOT INTEL OR ITS SUBCONTRACTOR WAS NEGLIGENT IN THE DESIGN, MANUFACTURE, OR WARNING OF THE INTEL PRODUCT OR ANY OF ITS PARTS.

Intel may make changes to specifications and product descriptions at any time, without notice.  Designers must not rely on the absence or characteristics of any features or instructions marked "reserved" or "undefined".  Intel reserves these for future definition and shall have no responsibility whatsoever for conflicts or incompatibilities arising from future changes to them.  The information here is subject to change without notice.  Do not finalize a design with this information.

The products described in this document may contain design defects or errors known as errata which may cause the product to deviate from published specifications.  Current characterized errata are available on request.

Contact your local Intel sales office or your distributor to obtain the latest specifications and before placing your product order.

Copies of documents which have an order number and are referenced in this document, or other Intel literature, may be obtained by calling 1-800-548-4725, or go to:  http\://www.intel.com/design/literature.htm.
Intel and the Intel logo are trademarks of Intel Corporation in the U.S. and/or other countries. 

\* Other names and brands may be claimed as the property of others.

This product includes software developed by the OpenSSL Project for use in the OpenSSL Toolkit. (http\://www.openssl.org/)

Copyright |copy| 2012-2013 Intel Corporation. All rights reserved.
