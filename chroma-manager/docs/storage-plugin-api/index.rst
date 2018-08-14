
Storage Plugin Developer's Guide for Integrated Manager for Lustre software
========================================================================

Introduction
------------

Storage plugins are responsible for delivering information about
entities that are not part of the Linux\*/Lustre\* stack.  This primarily means
storage controllers and network devices, but the plugin system is generic and 
does not limit the type of objects that can be reported.

To present device information to the manager server, a Python\* module is written using
the Storage Plugin API described in this document:

* The objects to be reported are described by declaring a series of
  Python classes: :ref:`storage_resources`
* Certain of these objects are used to store the contact information
  such as IP addresses for managed devices: :ref:`scannable_storage_resources`
* A main plugin class is implemented to provide required hooks for
  initialization and teardown: :ref:`storage_plugins`

The API is designed to minimize the lines of code required to write a plugin, 
minimize the duplication of effort between different plugins, and make as much
of the plugin code as possible declarative in style to minimize the need for 
per-plugin testing.  For example, rather than having plugins procedurally
check for resources that are in bad states during an update, we provide the means to declare
conditions that are automatically checked.  Similarly, rather than requiring explicit 
notification from the plugin when a resource attribute is changed, we detect
assignments to attributes and schedule transmission of updates in the background.

Plugins can provide varying levels of functionality.  The most basic plugins can provide
only discovery of storage resources at the time the plugin is loaded (requiring a manual
restart to detect any changes).  Most plugins will provide at least the initial discovery
and live detection of added/removed resources of certain classes, for example LUNs
as they are created and destroyed.  On a per-resource-class basis, alert conditions
can be added to report issues with the resources such as pools being rebuilt or 
physical disks that fail.

In addition to reporting a set of resources, plugins report a set of relationships between
the resources, used for associating problems with one resource with another resource.  This 
takes the form of an "affects" relationship between resources, for example the health of 
a physical disk affects the health of its pool, and the health of a pool affects LUNs
in that pool.  These relationships allow the effects of issues to be traced all the 
way up to the Lustre file system level and an appropriate drill-down user interface to be provided.

The API may change over time.  To ensure plugins are able to run against a particular
version of the API, each plugin module must declare the version of the API it intends to use.
The manager server will check the version of each plugin when loading and write a message to
the log if there is a problem.  The manager server supports version |api_version| of the API.
The plugin needs to declare the version in the top level module file where the
plugins and resources are defined.  Note, that if you have Python errors that prevent the plugin module
from importing, the version is not checked.  The version is only validated on cleanly imported plugins.
See the example plugin below for details on how to specify the version in your plugins.


Terminology
~~~~~~~~~~~

plugin
  A Python module providing a number of classes inheriting from the
  Plugin and Resource classes.

resource class
  A subclass of Resource declaring a means of identification, attributes,
  statistics and alert conditions.

resource
  An instance of a particular resource class, with a unique identifier.


.. _storage_resources:

Declaring Resources
-------------------

A `Resource` represents a single, uniquely identified object.  It may be a physical
device such as a physical hard drive, or a virtual object such as a storage pool or 
virtual machine.

.. code-block:: python

   from chroma_core.lib.storage_plugin.api import resources, identifiers, attributes, statistics

   class HardDrive(resources.Resource):
       serial_number = attributes.String()
       capacity = attributes.Bytes()
       temperature = statistics.Gauge(units = 'C')

       class Meta:
           identifier = identifiers.GlobalId('serial_number')

In general, storage resources may inherit from Resource directly, but
optionally they may inherit from a built-in resource class as a way of 
identifying common resource types for presentation purposes.  See 
:ref:`storage_plugin_builtin_resource_classes` for the available built-in
resource types.

Attributes
~~~~~~~~~~

The ``serial_number`` and ``capacity`` attributes of the HardDrive class are
from the ``attributes`` module.  These are special classes which:

* Apply validation conditions to the attributes
* Act as metadata for the presentation of the attribute in the manager server user interface

Various attribute classes are available for use, see :ref:`storage_plugin_attribute_classes`.

Attributes may be optional or mandatory.  They are mandatory by default. To 
make an attribute optional, pass ``optional = True`` to the constructor.

Statistics
~~~~~~~~~~

The ``temperature`` attribute of the HardDrive class is an example of
a resource statistic. Resource statistics differ from resource
attributes in the way they are presented to the user.  See :ref:`storage_plugin_statistic_classes`
for more on statistics.

Statistics are stored at runtime by assigning to the relevant
attribute of a storage resource instance.  For example, for a 
``HardDrive`` instance ``hd``, assigning ``hd.temperature = 20`` updates
the statistic.

Identifiers
~~~~~~~~~~~

Every Resource subclass is required to have an ``identifier`` attribute
that declares which attributes are to be used to uniquely identify the resource.

If a resource has a universally unique name and may be reported from more than one
place (for example, a physical disk which may be reported from more than one 
controller), use ``chroma_core.lib.storage_plugin.api.identifiers.GlobalId``.  For example, 
in the ``HardDrive`` class described above, each drive has a unique factory-assigned ID.

If a resource has an identifier that is scoped to a *scannable* storage resource or
a resource always belongs to a particular scannable storage resource, use
``chroma_core.lib.storage_plugin.api.identifiers.ScopedId``.

Either of the above classes is initialized with a list of attributes which
in combination are a unique identifier.  For example, if a true hard drive 
identifier is unavailable, a drive might be identified within a particular couplet 
by its shelf and slot number, like this:
::

    class HardDrive(Resource):
        class Meta:
            identifier = identifiers.ScopedId('shelf', 'slot')
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()

If a resource is created by users that doesn't have a natural unique
set of attributes, you can use ``identifiers.AutoId()`` to have
an internal ID assigned.  This is only valid for ScannableResource subclasses, and will
allow the user to create more than one identical resource. Therefore, use with care.

Relationships
~~~~~~~~~~~~~

The ``update_or_create`` function used to report resources (see :ref:`storage_plugins`) 
takes a ``parents`` argument, which is a list of the resources that directly affect the 
status of this resource.  This relationship does not imply ownership, but rather "a problem 
with parent is a problem with child" relationship.  For example,
a chain of relationships might be Fan->Enclosure->Physical disk->Pool->LUN.  
The graph of these relationships must be acyclic.

Although plugins will run without any parent relationships, it is important
to populate them so that hardware issues can be associated with the relevant
Lustre target or file system.

Alert Conditions
~~~~~~~~~~~~~~~~

Plugins can communicate error states by declaring *Alert conditions*,
which monitor the values of resource attributes and display alerts in the
manager server user interface when an error condition is encountered.

Alert conditions are specified for each resource in the Meta section, like this:
::

    class HardDrive(Resource):
        class Meta:
            identifier = identifiers.ScopedId('shelf', 'slot')
            alert_conditions = [
                alert_conditions.ValueCondition('status', warn_states = ['FAILED'], message = "Drive failure")
               ] 
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        status = attributes.String()

Several types of alert conditions are available. See :ref:`storage_plugin_alert_conditions`.

If a resource has more than one alert condition that refers to the same attribute, it is
necessary to add an `id` argument to allow each alert condition to be uniquely identified.  For example:
::

    class HardDrive(Resource):
        class Meta:
            identifier = identifiers.ScopedId('shelf', 'slot')
            alert_conditions = [
                alert_conditions.ValueCondition('status', warn_states = ['NEARFAILURE'], message = "Drive near failure", id = 'nearfailure'),
                alert_conditions.ValueCondition('status', warn_states = ['FAILED'], message = "Drive failure", id = 'failure')
               ] 
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        status = attributes.String()

You can tell if it is necessary to add an explicit ID by looking for an error in the
output of the validation process (:ref:`validation`) -- if a plugin passes validation without `id`
arguments to alert conditions, it is recommended that `id` be omitted.



.. _scannable_storage_resources:

Declaring a ScannableResource
-----------------------------

Certain storage resources are considered 'scannable':

* They can be added by the administrator using the manager server user interface
* Plugins contact this resource to learn about other resources
* This resource 'owns' some other resources

A typical scannable resource is a storage controller or couplet of
storage controllers.

::

   from chroma_core.lib.storage_plugin.api import attributes, identifiers, resources

   class StorageController(resources.ScannableResource):
       address_1 = attributes.Hostname()
       address_2 = attributes.Hostname()

       class Meta:
           identifier = identifiers.GlobalId('address_1', 'address_2')

.. _storage_plugins:

Implementing a Plugin
---------------------

The Resource classes are simply declarations of what resources can be 
reported by the plugin and what properties they will have.  The plugin module
must also contain a subclass of *Plugin* which implements at least the
``initial_scan`` function:

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.initial_scan

Within ``initial_scan``, plugins use the ``update_or_create`` function to 
report resources.

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.update_or_create

If any resources are allocated in ``initial_scan``, such as threads or 
sockets, they may be freed in the ``teardown`` function:

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.teardown

After initialization, the ``update_scan`` function will be called periodically.
You can set the delay between ``update_scan`` calls by assigning to
``self.update_period`` before leaving in ``initial_scan``.  Assignments to
``update_period`` after ``initial_scan`` will have no effect.

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.update_scan

If a resource has changed, you can either use ``update_or_create`` to modify 
attributes or parent relationships, or you can directly assign to the resource's 
attributes or use its add_parent and remove_parent functions.  If a resource has 
gone away, use ``remove`` to remove it:

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.remove

Although resources must be reported synchronously during ``initial_scan``, this
is not the case for updates.  For example, if a storage device provides asynchronous
updates via a network protocol, the plugin author may spawn a thread in ``initial_scan``
that listens for these updates.  The thread listening for updates may modify resources
and make ``update_or_create`` and ``remove`` calls on the plugin object.
Plugins written in this way would probably not implement ``update_scan`` at all.

Logging
~~~~~~~

Plugins should refrain from using ``print`` or any custom logging, in favor of
using the ``log`` attribute of the Plugin instances, which is a standard Python
``logging.Logger`` object provided to each plugin.

The following shows the wrong and right ways to emit log messages:
::

        # BAD: do not use print
        print "log message"

        # BAD: do not create custom loggers
        logging.getLogger('my_logger').info("log message")

        # Good: use the provided logger
        self.log.info("log message")

Presentation Metadata
---------------------

Names
~~~~~

Sensible defaults are used wherever possible when presenting UI elements
relating to storage resources.  For example, by default, attribute names are
transformed to capitalized text. For example,``file_size`` is transformed to *File size*.  When a different
name is desired, the plugin author can provide a ``label`` argument to attribute 
constructors:

::

   my_internal_name = attributes.String(label = 'Fancy name')

Resource classes are by default referred to by their Python class name, qualified
with the plugin module name.  For example, if the ``acme`` plugin had a class called
``HardDrive``, it would be called ``acme.HardDrive``.  This can be overridden by setting
the ``label`` attribute on the Meta attribute of a Resource class.

Instances of resources have a default human readable version of their class name followed by
their identifier attributes.  This can be overridden by implementing the ``get_label``
function on the storage resource class, returning a string or unicode string for the instance.

Charts
~~~~~~

By default, the manager server web interface presents a separate chart for each statistic
of a resource.  However, it is often desirable to group statistics on the same
chart, such as a read/write bandwidth graph.  This may be done by setting the ``charts``
attribute on a resource class to a list of dictionaries, where each dictionary
has a ``title`` element with a string value and a ``series`` element whose value
is a list of statistic names to plot together.

When two or more series are plotted together, they must be of the same type (time series or histogram).  They do
not have to be in the same units, but only up to two different units may be 
used on the same chart (one Y axis on either side of the chart).

For example, the following resource has a ``charts`` attribute which presents
the read and write bandwidth on the same chart:

::

    class MyResource(Resource):
        read_bytes_per_sec = statistics.Gauge(units = 'bytes/s')
        write_bytes_per_sec = statistics.Gauge(units = 'bytes/s')

        class Meta:
            charts = [
                {
                    'title': "Bandwidth",
                    'series': ['read_bytes_per_sec', 'write_bytes_per_sec']
                }
            ]


Running a Plugin
----------------

.. _validation:

Validating
~~~~~~~~~~

Before running your plugin as part of a manager server instance, it is a good idea to check it over
using the `validate_storage_plugin` command:

::

    $ cd /usr/share/chroma-manager
    $ ./manage.py validate_storage_plugin /tmp/my_plugin.py
    Validating plugin 'my_plugin'...
    OK

Installing
~~~~~~~~~~

Plugins are loaded according to the ``settings.INSTALLED_STORAGE_PLUGINS`` variable.  This variable
is a list of module names within the Python import path.  If your plugin is located
at ``/home/developer/project/my_plugin.py``, create a ``local_settings.py`` file
in the ``chroma-manager`` directory (``/usr/share/chroma-manager`` when installed
from RPM) with the following content:

::

    sys.path.append("/home/developer/project/")
    INSTALLED_STORAGE_PLUGINS.append('my_plugin')

After modifying this setting, restart the manager server services.

Errors from the storage plugin subsystem, including any errors output
from your plugin can be found in `/var/log/chroma/storage_plugin.log`. To
increase the verbosity of the log output (by default only WARN and above
is output), add your plugin to ``settings.STORAGE_PLUGIN_DEBUG_PLUGINS``.
Changes to these settings take effect when the manager server services are
restarted.

Running the Plugin Process Separately
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During development, the process that hosts storage plugins can be run separately,
so that it can be stopped and started quickly by plugin developers:

::

    cd /usr/share/chroma-manager
    supervisorctl -c production_supervisord.conf stop plugin_runner
    ./manage.py chroma_service --verbose plugin_runner

Correlating Controller Resources with Linux Devices Using Relations
-------------------------------------------------------------------

As well as explicit *parents* relations between resources, resource attributes can be 
declared to *provide* a particular entity.  This is used for linking up resources between
different plugins, or between storage controllers and Linux hosts.

To match up two resources based on their attributes, use the `Meta.relations` attribute,
which must be a list of `relations.Provide` and `relations.Subscribe` objects.  In the following
example, a plugin matches its LUNs to detected SCSI devices of the built in class `linux.ScsiDevice`,
which stores the device's WWID as the `serial` attribute.


.. code-block:: python

    class MyLunClass(Resource):
        serial = attributes.String()

        class Meta:
            identifier = identifiers.GlobalId('my_serial')
            relations = [relations.Provide(
                provide_to = ('linux', 'ScsiDevice'),
                attributes = 'serial')]


The `provide_to` argument to `Provide` can either be a resource class, or a 2-tuple of `([plugin name], [class name])`
for referring to resources in another plugin.  In this case, we are referring to a resource in the 'linux' plugin, which
is what the manager server uses for detecting standard devices and device nodes on Linux servers.  Note that these
relations are case sensitive.

Example Plugin
--------------

.. literalinclude:: /../../tests/unit/chroma_core/lib/storage_plugin/example_plugin.py
   :language: python
   :linenos:

Reference
---------

.. _storage_plugin_attribute_classes:

Resource Attributes
-------------------

Common Options
~~~~~~~~~~~~~~

.. automethod:: chroma_core.lib.storage_plugin.base_resource_attribute.BaseResourceAttribute.__init__


Available Attribute Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: chroma_core.lib.storage_plugin.api.attributes
   :members:
   :exclude-members: ResourceReference

.. autoclass:: chroma_core.lib.storage_plugin.api.attributes.ResourceReference

.. _storage_plugin_statistic_classes:

Statistic Classes
-----------------

.. automodule:: chroma_core.lib.storage_plugin.api.statistics
   :members:

.. _storage_plugin_builtin_resource_classes:

Built-in Resource Classes
-------------------------

.. automodule:: chroma_core.lib.storage_plugin.api.resources
   :members:

.. _storage_plugin_alert_conditions:

Alert Conditions
----------------

.. automodule:: chroma_core.lib.storage_plugin.api.alert_conditions
    :members:


Advanced: Using Custom Block Device Identifiers
-----------------------------------------------

A best effort is made to extract standard SCSI identifiers from block devices that
are encountered on Lustre servers.  However, in some cases:

* The SCSI identifier may be missing
* The storage controller may not provide the SCSI identifier

Storage plugins may provide additional code to run on Lustre servers that extracts additional
information from block devices.

Agent Plugins
~~~~~~~~~~~~~

Plugin code running within the chroma-agent service has a simple interface:

.. autoclass:: chroma_agent.plugin_manager.DevicePlugin
  :members: start_session, update_session

Implementing `update_session` is optional. Plugins that do not implement this function will only send
information to the server once when the agent begins its connection to the server.

The agent guarantees that the instance of your plugin class is persistent within the process
between the initial call to start_session and subsequent calls to update_session, and that
start_session will only ever be called once for a particular instance of your class.  This allows
you to store information in start_session that is used for calculating deltas of the system
information to send in update_session.

To install an agent plugin like this, copy the .py file containing a DevicePlugin subclass into
`/usr/lib/python2.[46]/site-packages/chroma_agent-*.egg/chroma_agent/device_plugins/` on the
servers with chroma-agent installed, and restart the chroma-agent service.  Test the output
of your plugin with `chroma-agent device-plugin --plugin=my_controller` (if for example
your plugin file was called my_controller.py).

The name of the agent plugin module must exactly match the name of the plugin module running
on the manager server server.

Handling Data from Agent Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The information sent by an agent plugin is passed on to the server plugin with the same name.  To handle
this type of information, the plugin must implement two methods:

.. autoclass:: chroma_core.lib.storage_plugin.api.plugin.Plugin
  :members: agent_session_start, agent_session_continue

Advanced: Reporting Hosts
-------------------------

Your storage hardware may be able to provide server addresses, for example
if the storage hardware hosts virtual machines that act as Lustre servers.

To report these hosts from a storage plugin, create resources of a class with
subclasses `resources.VirtualMachine`.

.. code-block:: python

    class MyController(resources.ScannableResource):
        class Meta:
            identifier = identifiers.GlobalId('address')
        address = attributes.Hostname()

    class MyVirtualMachine(resources.VirtualMachine):
        class Meta:
            identifier = identifiers.GlobalId('vm_id', 'controller')

        controller = attributes.ResourceReference()
        vm_id = attributes.Integer()
        # NB the 'address' attribute is inherited

    class MyPlugin(plugin.Plugin):
        def initial_scan(self, controller):
            # ... somehow learn about a virtual machine hosted on `controller` ...
            self.update_or_create(MyVirtualMachine, vm_id = 0, controller = controller, address = "192.168.1.11")

When a new VirtualMachine resource is created by a plugin, the configuration
process is the same as if the host had been added via the manager server user interface, and the added host 
will appear in the list of servers in the user interface.

Advanced: Specifying Homing Information
---------------------------------------

A given device node (i.e. presentation of a LUN) may be a more or less preferable means
of access to a storage device.  For example:

* If a single LUN is presented on two controller ports, a device node on a host connected to one port 
  may be preferable to a device node on a host connected to the other port.
* If a LUN is accessible via two device nodes on a single server, one may be preferable to the other.

This type of information allows the manager server to make an intelligent selection of primary/secondary Lustre servers.

To express this information, create a PathWeight resource that is a parent of the device node and has as its
parent the LUN.

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
