
Chroma storage plugin developer's guide
=======================================

Introduction
------------

Within Chroma, storage plugins are responsible for delivering information about
entities which are not part of the Linux/Lustre stack.  This primarily means
storage controllers and network devices, but the plugin system is generic and 
does not limit the type of objects that can be reported.

To present device information to Chroma, a python module is written using
the API described in this document:

* The objects to be reported are described by declaring a series of
  python classes: :ref:`storage_resources`
* Certain of these objects are used to store the contact information
  such as IP addresses for managed devices: :ref:`scannable_storage_resources`
* A main plugin class is implemented to provide required hooks for
  initialization and teardown: :ref:`storage_plugins`

The API is designed to minimize the lines of code required to write a plugin, 
minimize the duplication of effort between different plugins, and make as much
of the plugin code as possible declarative in style to minimize the need for 
per-plugin testing.  For example, rather than having plugins procedurally
check for resource in bad states during an update, we provide the means to declare
conditions which are automatically checked.  Similarly, rather than requiring explicit 
notification from the plugin when a resources attributes are changed, we detect
assignment to attributes and schedule transmission of updates in the background.

Plugins can provide varying levels of functionality.  The most basic plugins can provide
only discovery of storage resources at the time the plugin is loaded (requiring a manual
restart to detect any changes).  Most plugins would provide at least the initial discovery
and live detection of added/removed resources of certain classes, for example LUNs
as they are created and destroyed.  On a per-resource-class basis, alert conditions
can be added to report issues with the resources such as pools being rebuilt or 
physical disks which fail.

In addition to reporting a set of resources, plugins report a set of relationships between
the resources, used for associating problems with one resource with another resource.  This 
takes the form of an "affects" relationship between resources, for example the health of 
a physical disk affects the health of its pool, and the health of a pool affects LUNs
in that pool.  These relationships allow Chroma to trace the effects of issues all the 
way up to the Lustre filesystem level and provide an appropriate drill-down user interface.

Terminology
~~~~~~~~~~~

plugin
  A python module providing a number of classes inheriting from Chroma's
  Plugin and Resource classes.

resource class
  A subclass of Resource declaring a means of identification, attributes,
  statistics and alert conditions.

resource
  An instance of a particular resource class, with a unique identifier.


.. _storage_resources:

Declaring Resources
--------------------------

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
           identifier = GlobalId('serial_number')

In general storage resources may inherit from Resource directly, but
optionally they may inherit from a built-in resource class as a way of 
identifying common resource types to Chroma for presentation purposes.  See 
:ref:`storage_plugin_builtin_resource_classes` for the available built-in
resource types.

Attributes
~~~~~~~~~~

The ``serial_number`` and ``capacity`` attributes of the HardDrive class are
from the ``attributes`` module.  These are special classes which:

* apply validation conditions to the attributes
* act as metadata for the presentation of the attribute in the user interface

Various attribute classes are available for use, see :ref:`storage_plugin_attribute_classes`.

Attributes may be optional or mandatory.  They are mandatory by default, to 
make an attribute optional, pass ``optional = True`` to the constructor.

Statistics
~~~~~~~~~~

The ``temperature`` attribute of the HardDrive class is an example of
a resource statistic.  Resource statistics differ from resource
attributes in the way they are presented to the user.  See :ref:`storage_plugin_statistic_classes`
for more on statistics.

Statistics are stored at runtime by assigning to the relevant
attribute of a storage resource instance.  For example, if we had a 
``HardDrive`` instance ``hd``, doing ``hd.temperature = 20`` would update
the statistic.

Identifiers
~~~~~~~~~~~

Every Resource subclass is required to have an ``identifier`` attribute
which declares which attributes are to be used to uniquely identify the resource.

If a resource has a universally unique name and may be reported from more than one
place (for example, a physical disk which might be reported from more than one 
controller), use ``chroma_core.lib.storage_plugin.api.identifiers.GlobalId``.  This is the
case for the example ``HardDrive`` class above, which has a factory-assigned ID 
for the drive.

If a resource has an identifier which is scoped to a *scannable* storage resource or
it always belongs to a particular scannable storage resource, then use
``chroma_core.lib.storage_plugin.api.identifiers.ScopedId``.

Either of the above classes is initialized with a list of attributes which
in combination are a unique identifier.  For example, if a true hard drive 
identifier was unavailable, a drive might be identified within a particular couplet 
by its shelf and slot number, like this:
::

    class HardDrive(Resource):
        class Meta:
            identifier = ScopedId('shelf', 'slot')
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()

If there is a resource that is created by users and doesn't have a natural unique
set of attributes, you can use ``identifiers.AutoId()`` to have Chroma assign
an internal ID.  This is only valid for ScannableResource subclasses, and will
allow the user to create more than one identical resource: use with care.

Relationships
~~~~~~~~~~~~~

The ``update_or_create`` function used to report resources (see :ref:`storage_plugins`) 
takes a ``parents`` argument which is the list of which directly affect the 
status of this resource.  This relationship does not imply ownership, rather 
a "a problem with parent is a problem with child" relationship.  For example,
a chain of relationships might go Fan->Enclosure->Physical disk->Pool->LUN.  
The graph of these relationships must be acyclic.

Although plugins will run without any parent relationships at all, it is important
to populate them so that Chroma can associate hardware issues with the relevant
Lustre target/filesystem.

Alert conditions
~~~~~~~~~~~~~~~~

Plugins may communicate error states to Chroma by declare *Alert conditions*
which monitor the values of resource attributes and display alerts in the
Chroma Manager user interface when an error condition is encountered.

Alert conditions are specified for each resource in the Meta section, like this:
::

    class HardDrive(Resource):
        class Meta:
            identifier = ScopedId('shelf', 'slot')
            alert_conditions = [
                alert_conditions.ValueCondition('status', warn_states = ['FAILED'], message = "Drive failure")
               ] 
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        status = attributes.String()

There are several types of alert condition available, see :ref:`storage_plugin_alert_conditions`

If a resource has more than one alert condition which refers to the same attribute, it is
necessary to add an `id` argument to allow Chroma to uniquely identify each one.  For example:
::

    class HardDrive(Resource):
        class Meta:
            identifier = ScopedId('shelf', 'slot')
            alert_conditions = [
                alert_conditions.ValueCondition('status', warn_states = ['NEARFAILURE'], message = "Drive near failure", id = 'nearfailure'),
                alert_conditions.ValueCondition('status', warn_states = ['FAILED'], message = "Drive failure", id = 'failure')
               ] 
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        status = attributes.String()

You can tell if it is necessary to add an explicit ID by looking for an error in the
output of validation (:ref:`validation`) -- if a plugin passes validation without `id`
arguments to alert conditions, it is recommended to omit `id`.



.. _scannable_storage_resources:

Declaring a ScannableResource
------------------------------------

Certain storage resources are considered 'scannable':

* They can be added by the administrator using the user interface
* Plugins contact this resource to learn about other resources
* This resource 'owns' some other resources

A typical scannable resource is a storage controller or couplet of
storage controllers.

::

   from chroma_core.lib.storage_plugin.api import resources
   from chroma_core.lib.storage_plugin.api import identifiers
   from chroma_core.lib.storage_plugin.api import attributes

   class StorageController(resources.ScannableResource):
       address_1 = attributes.Hostname()
       address_2 = attributes.Hostname()

       class Meta:
           identifier = identifiers.GlobalId('address_1', 'address_2')

.. _storage_plugins:

Implementing Plugin
--------------------------

The Resource classes are simply declarations of what resources can be 
reported by the plugin, and what properties they will have.  The plugin module
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
attributes, or use its add_parent and remove_parent functions.  If a resource has 
gone away, use ``remove`` to notify Chroma:

.. automethod:: chroma_core.lib.storage_plugin.api.plugin.Plugin.remove

Although resources must be reported synchronously during ``initial_scan``, this
is not the case for updates.  For example, if a storage device provides asynchronous
updates via a network protocol, the plugin author may spawn a thread in ``initial_scan``
which listens for these updates.  The thread listening for updates may modify resources
and make ``update_or_create`` and ``remove`` calls on the plugin object.
Plugins written in this way would probably not implement ``update_scan`` at all.

Logging
~~~~~~~

Plugins should refrain from using ``print`` or any custom logging, in favor of
using the ``log`` attribute of Plugin instances, which is a standard python
``logging.Logger`` object which Chroma provides to each plugin.

The following shows the wrong and right ways to emit log messages:
::

        # BAD: do not use print
        print "log message"

        # BAD: do not create custom loggers
        logging.getLogger('my_logger').info("log message")

        # Good: use the provided logger
        self.log.info("log message")

Presentation metadata
---------------------

Names
~~~~~

Chroma will use sensible defaults wherever possible when presenting UI elements
relating to storage resources.  For example, by default attribute names are
transformed to capitalized prose, like ``file_size`` to *File size*.  When a different
name is desired, the plugin author may provide a ``label`` argument to attribute 
constructors:

::

   my_internal_name = attributes.String(label = 'Fancy name')

Resource classes are by default referred to by their python class name, qualified
with the plugin module name.  For example, if the ``acme`` plugin had a class called
``HardDrive`` then it would be called ``acme.HardDrive``.  This can be overridden by setting
the ``label`` attribute on the Meta attribute of a Resource class.

Instances of resources have a default human readable name of their class name followed by
their identifier attributes.  This can be overridden by implementing the ``get_label``
function on the storage resource class, returning a string or unicode string for the instance.

Charts
~~~~~~

By default, the Chroma web interface presents a separate chart for each statistic
of a resource.  However, it is often desirable to group statistics on the same
chart, such as a read/write bandwidth graph.  This may be done by setting the ``charts``
attribute on a resource class to a list of dictionaries, where each dictionary
has a ``title`` element with a string value, and a ``series`` element whose value
is a list of statistic names to plot together.

The series plotted together must be of the same type (time series or histogram).  They do
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


Running a plugin
----------------

.. _validation:

Validating
~~~~~~~~~~

Before running your plugin as part of a Chroma Manager instance, it is a good idea to check it over
using the `validate_storage_plugin` command provided with Chroma Manager:

::

    $ cd /usr/share/chroma-manager
    $ ./manage.py validate_storage_plugin /tmp/my_plugin.py
    Validating plugin 'my_plugin'...
    OK

Installing
~~~~~~~~~~

Chroma loads plugins specified by the ``settings.INSTALLED_STORAGE_PLUGINS``.  This variable
is a list of module names within the python import path.  If your plugin is located
at ``/home/developer/project/my_plugin.py`` then you would create a ``local_settings.py`` file
in the ``chroma-manager`` directory (``/usr/share/chroma-manager`` when installed
from RPM) with the following content:

::

    sys.path.append("/home/developer/project/")
    INSTALLED_STORAGE_PLUGINS.append('my_plugin')

After modifying this setting, restart the Chroma manager services.

Errors from the storage plugin subsystem, including any errors output
from your plugin may be found in `/var/log/chroma/storage_plugin.log`. To
increase the verbosity of the log output (by default only WARN and above
is output), add your plugin to ``settings.STORAGE_PLUGIN_DEBUG_PLUGINS``.
Changes to these settings take effect when the Chroma Manager services are restarted.

Running separately
~~~~~~~~~~~~~~~~~~

The process which hosts storage plugins may be run separately to the usual
Chroma services, so that it may be stopped and started quickly by
plugin developers:

::

    service chroma-storage stop
    cd /usr/share/chroma-manager
    chroma_core/bin/storage_daemon -f

Correlating controller resources with Linux devices using relations
---------------------------------------------------------------------

As well as explicit *parents* relations between resources, resource attributes can be 
declared to *provide* a particular entity.  This is used for linking up resource between
different plugins, or between storage controllers and Linux hosts.

SCSI devices detected by Chroma have two serial number attributes called `serial_80` and
`serial_83`: these correspond to the output of the `scsi_id` tool when using `-p 0x80` or
`-p 0x83` arguments respectively.

To match up two resources based on their attributes, use the `Meta.relations` attribute,
which must be a list of `relations.Provide` and `relations.Subscribe` objects.

.. code-block:: python

    class MyLunClass(Resource):
        serial_80 = attributes.String()

        class Meta:
            identifier = identifiers.GlobalId('my_serial')
            relations = [relations.Provide(
                provide_to = ('linux', 'ScsiDevice'),
                attributes = 'serial_80')]


The `provide_to` argument to `Provide` can either be a resource class, or a 2-tuple of `([plugin name], [class name])`
for referring to resources in another plugin.  In this case we are referring to a resource in the 'linux' plugin which
is what Chroma Manager uses for detecting standard devices and device nodes on Linux servers.

Example plugin
--------------

.. literalinclude:: /../../tests/unit/chroma_core/lib/storage_plugin/example_plugin.py
   :language: python
   :linenos:

Reference
---------

.. _storage_plugin_attribute_classes:

Resource attributes
-------------------

Common options
~~~~~~~~~~~~~~

.. automethod:: chroma_core.lib.storage_plugin.base_resource_attribute.BaseResourceAttribute.__init__


Available attribute classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: chroma_core.lib.storage_plugin.api.attributes
   :members:
   :exclude-members: ResourceReference

.. autoclass:: chroma_core.lib.storage_plugin.api.attributes.ResourceReference

.. _storage_plugin_statistic_classes:

Statistic classes
----------------------------

.. automodule:: chroma_core.lib.storage_plugin.api.statistics
   :members:

.. _storage_plugin_builtin_resource_classes:

Built-in resource classes
------------------------------------

.. automodule:: chroma_core.lib.storage_plugin.api.resources
   :members:

.. _storage_plugin_alert_conditions:

Alert conditions
----------------

.. automodule:: chroma_core.lib.storage_plugin.api.alert_conditions
    :members:


Advanced: using custom block device identifiers
-----------------------------------------------

Chroma makes a best effort to extract standard SCSI identifiers from block devices which
it encounters on Lustre servers.  However, in some cases:

* The SCSI identifier may be missing
* The storage controller may not provide the SCSI identifier

Storage plugins may provide additional code to run on Lustre servers which extracts additional
information from block devices.

Agent plugins
~~~~~~~~~~~~~

Plugin code running within the Chroma agent has a simple interface:

.. autoclass:: chroma_agent.plugins.DevicePlugin
  :members: start_session, update_session

Implementing `update_session` is optional: plugins which do not implement this function will only send
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
on Chroma Manager.

Handling data from agent plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The information sent by an agent plugin is passed on to the server plugin with the same name.  To handle
this type of information, the plugin must implement two methods:

.. autoclass:: chroma_core.lib.storage_plugin.api.plugin.Plugin
  :members: agent_session_start, agent_session_continue

Advanced: reporting hosts
-------------------------

Your storage hardware may be able to provide Chroma with knowledge of server addresses, for example
if the storage hardware hosts virtual machines which act as Lustre servers.

To report these hosts from a storage plugin, create resources of a class which
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

When a new VirtualMachine resource is created by a plugin, Chroma Manager goes through the same configuration
process as if the host had been added via the user interface, and the added host will appear in the list of
servers in the user interface.

Advanced: specifying homing information
---------------------------------------

A given device node (i.e. presentation of a LUN) may be a more or less preferable means
of access to a storage device.  For example:

* if a single LUN is presented on two controller ports then a device node on a host connected to one port may be preferable to a device node on a host connected to the other port.
* if a LUN is accessible via two device nodes on a single server, then one may be preferable to the other

This type of information allows Chroma Manager to make intelligent selection of primary/secondary Lustre servers.

To express this information, create a PathWeight resource which is a parent of the device node, and has as its
parent the LUN.
