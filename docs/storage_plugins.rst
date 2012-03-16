
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
  StoragePlugin and StorageResource classes.

resource class
  A subclass of StorageResource declaring a means of identification, attributes,
  statistics and alert conditions.

resource
  An instance of a particular resource class, with a unique identifier.


.. _storage_resources:

Declaring StorageResources
--------------------------

A `StorageResource` represents a single, uniquely identified object.  It may be a physical
device such as a physical hard drive, or a virtual object such as a storage pool or 
virtual machine.

.. code-block:: python

   from chroma_core.lib.storage_plugin.resource import StorageResource, GlobalId
   from chroma_core.lib.storage_plugin import attributes, statistics

   class HardDrive(StorageResource):
       serial_number = attributes.String()
       capacity = attributes.Bytes()
       temperature = statistics.Gauge(units = 'C')

       identifier = GlobalId('serial_number')

In general storage resources may inherit from StorageResource directly, but
optionally they may inherit from a built-in resource class as a way of 
identifying common resource types to Chroma for presentation purposes.  See 
:ref:`storage_plugin_builtin_resource_classes` for the available built-in
resource types.

Attributes
~~~~~~~~~~

The ``serial_number`` and ``capacity`` attributes of the HardDrive class are
StorageResourceAttributes.  These are special classes which:

* apply validation conditions to the attributes
* act as metadata for the presentation of the attribute in the user interface

Various attribute classes are available for use, see :ref:`storage_plugin_attribute_classes`.

Attributes may be optional or mandatory.  They are mandatory by default, to 
make an attribute optional, pass ``optional = True`` to the constructor.

Statistics
~~~~~~~~~~

The ``temperature`` attribute of the HardDrive class is an example of
a StorageResourceStatistic.  Resource statistics differ from resource
attributes in the way they are presented to the user.  See :ref:`storage_plugin_statistic_classes`
for more on statistics.

Statistics are stored at runtime by assigning to the relevant
attribute of a storage resource instance.  For example, if we had a 
``HardDrive`` instance ``hd``, doing ``hd.temperature = 20`` would update
the statistic.

Identifiers
~~~~~~~~~~~

Every StorageResource subclass is required to have an ``identifier`` attribute
which declares which attributes are to be used to uniquely identify the resource.

If a resource has a universally unique name and may be reported from more than one
place (for example, a physical disk which might be reported from more than one 
controller), use ``chroma_core.lib.storage_plugin.resource.GlobalId``.  This is the
case for the example ``HardDrive`` class above, which has a factory-assigned ID 
for the drive.

If a resource has an identifier which is scoped to a *scannable* storage resource or
it always belongs to a particular scannable storage resource, then use
``chroma_core.lib.storage_plugin.resource.ScannableId``.

Either of the above classes is initialized with a list of attributes which
in combination are a unique identifier.  For example, if a true hard drive 
identifier was unavailable, a drive might be identified within a particular couplet 
by its shelf and slot number, like this:
::

    class HardDrive(StorageResource):
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        identifier = ScannableId('shelf', 'slot')

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

Bad values of attributes may be declared using class attributes 
of the types from ``chroma_core.lib.storage_plugin.alert_conditions``,
see :ref:`storage_plugin_alert_conditions`

.. _scannable_storage_resources:

Declaring a ScannableStorageResource
------------------------------------

Certain storage resources are considered 'scannable':
* They can be added by the administrator using the user interface
* Plugins contact this resource to learn about other resources
* This resource 'owns' some other resources

The archetypal scannable resource is a storage controller or couplet of
storage controllers.

::

   from chroma_core.lib.storage_plugin.resource import ScannableStorageResource, GlobalId

   class StorageController(StorageResource):
       address_1 = attributes.Hostname()
       address_2 = attributes.Hostname()

       identifier = GlobalId('address_1', 'address_2')

.. _storage_plugins:

Implementing StoragePlugin
--------------------------

The StorageResource classes are simply declarations of what resources can be 
reported by the plugin, and what properties they will have.  The plugin module
must also contain a subclass of *StoragePlugin* which implements at least the
``initial_scan`` function:

.. automethod:: chroma_core.lib.storage_plugin.plugin.StoragePlugin.initial_scan

Within ``initial_scan``, plugins use the ``update_or_create`` function to 
report resources.

.. automethod:: chroma_core.lib.storage_plugin.plugin.StoragePlugin.update_or_create

If any resources are allocated in ``initial_scan``, such as threads or 
sockets, they may be freed in the ``teardown`` function:

.. automethod:: chroma_core.lib.storage_plugin.plugin.StoragePlugin.teardown

After initialization, the ``update_scan`` function will be called periodically.
You can set the delay between ``update_scan`` calls by assigning to
``self.update_period`` before leaving in ``initial_scan``.  Assignments to
``update_period`` after ``initial_scan`` will have no effect.

.. automethod:: chroma_core.lib.storage_plugin.plugin.StoragePlugin.update_scan

If a resource has changed, you can either use ``update_or_create`` to modify 
attributes or parent relationships, or you can directly assign to the resource's 
attributes, or use its add_parent and remove_parent functions.  If a resource has 
gone away, use ``remove`` to notify Chroma:

.. automethod:: chroma_core.lib.storage_plugin.plugin.StoragePlugin.remove

Although resources must be reported synchronously during ``initial_scan``, this
is not the case for updates.  For example, if a storage device provides asynchronous
updates via a network protocol, the plugin author may spawn a thread in ``initial_scan``
which listens for these updates.  The thread listening for updates may modify resources
and make ``update_or_create`` and ``remove`` calls on the plugin object.
Plugins written in this way would probably not implement ``update_scan`` at all.

Logging
~~~~~~~

Plugins should refrain from using ``print`` or any custom logging, in favor of
using the ``StoragePlugin.log`` object, which is a standard python
``logging.Logger`` object which Chroma provides to each plugin.

The following shows the wrong and right ways to emit log messages:
::

    def initial_scan(self, scannable_resource):
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
the ``class_label`` class attribute on a StorageResource class.

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

    class MyResource(StorageResource):
        read_bytes_per_sec = statistics.Gauge(units = 'bytes/s')
        write_bytes_per_sec = statistics.Gauge(units = 'bytes/s')

        charts = [
            {
                'title': "Bandwidth",
                'series': ['read_bytes_per_sec', 'write_bytes_per_sec']
            }
        ]


Running a plugin
----------------

Chroma loads plugins specified by the ``settings.INSTALLED_STORAGE_PLUGINS``.  This variable
is a list of module names within the python import path.  If your plugin is located
at ``/home/developer/project/my_plugin.py`` then you would create a ``local_settings.py`` file
in the ``hydra-server`` directory (``/usr/share/hydra-server`` when installed
from RPM) with the following content:

::

    sys.path.append("/home/developer/project/")
    INSTALLED_STORAGE_PLUGINS.append('my_plugin')

After modifying this setting, restart the hydra services.

Advanced: reporting virtual machines
------------------------------------

Most of the built-in resource types are purely for identification of 
common types of resource for presentation purposes.  However, the
``chroma_core.lib.storage_plugin.builtin_resources.VirtualMachine``
class is treated specially by Chroma.  When a resource of this class is
reported by a plugin, Chroma uses the ``address`` attribute of the 
resource to set up a Lustre server as if it had been added using the 
user interface.

The ``VirtualMachine`` resource is intended to be used for reporting 
virtual machines which are embedded on a particular storage controller.  To
indicate which controller this is, the resource must have the ``home_controller``
attribute set to a suitable resource.  This resource does not have to be of
a particular class, but must match the optional ``home_controller`` attribute
of the ``VirtualDisk`` class.  When these two fields match, the Lustre server
derived form the VirtualMachine resource is identified as the primary
access path for that particular ``VirtualDisk``.  The resulting user
experience is that the scannable resource (e.g. couplet) is added, the 
Lustre servers automatically appear, and the detected storage resources
are automatically set up for failover.

Correlating controller resources with Linux devices using ``provide``
---------------------------------------------------------------------

As well as explicit *parents* relations between resources, resource attributes can be 
declared to *provide* a particular entity.  This is used for linking up resource between
different plugins, or between storage controllers and Linux hosts.

Currently the only supported use of this is for correlating LUNs to Linux block devices
using SCSI IDs.  To take advantage of this functionality from a plugin, declare an attribute
containing the serial number like this:

::

    class MyLunClass(StorageResource):
        my_serial = attributes.String(provide='scsi_serial')

The 'magic' here is the 'scsi_serial' name -- this is the identifier that
Chroma knows can be used for matching up with SCSI IDs on Linux hosts.

Example plugin
--------------

.. literalinclude:: /../tests/unit/chroma_core/lib/storage_plugin/example_plugin.py
   :language: python
   :linenos:

Reference
---------

.. _storage_plugin_attribute_classes:

Attribute classes
----------------------------

.. automodule:: chroma_core.lib.storage_plugin.attributes
   :members:

.. _storage_plugin_statistic_classes:

Statistic classes
----------------------------

.. automodule:: chroma_core.lib.storage_plugin.statistics
   :members:

.. _storage_plugin_builtin_resource_classes:

Built-in resource classes
------------------------------------

.. automodule:: chroma_core.lib.storage_plugin.builtin_resources
   :members:

.. _storage_plugin_alert_conditions:

Alert conditions
----------------

.. automodule:: chroma_core.lib.storage_plugin.alert_conditions
    :members:



Advanced: using custom block device identifiers
-----------------------------------------------

If storage devices from your controllers do not appear on Linux servers with a globally unique
ID as the SCSI identifier, then you need some additional code to collect this information from
Lustre servers.

A stripped down agent-side component of plugins can be written.  When this is installed on 
Lustre servers, your plugin running on the Chroma manager will receive callbacks 

Advanced: reporting hosts
-------------------------

Your storage hardware may be able to provide Chroma with knowledge of server addresses, for example
if the storage hardware hosts virtual machines which act as Lustre servers.

Advanced: specifying access paths
---------------------------------

If you are using custom block device identifiers, you may not want the relationship to
be directly from the Lun on the controller to the block device on the server.  For example,
you may wish to report this relationship via network ports so that Chroma knows which
ports are related to which devices for performance analysis.

To do this, your plugin must somehow know the relationship between these ports and devices.
Assuming this knowledge exists, you can report the relationship from a device node to a server port, then to
a controller port, then to a LUN.  This chain of relationships would allow Chroma Manager to provide
for example a chart superimposing the bandwidth of each component in the chain from the device node to 
the storage target.

Advanced: specifying homing information
---------------------------------------

A given device node (i.e. presentation of a LUN) may be a more or less preferable means
of access to a storage device.  For example:
 * if a single LUN is presented on two controller ports then a device node on a host connected to one port may be preferable to a device node on a host connected to the other port.
 * if a LUN is accessible via two device nodes on a single server, then one may be preferable to the other

This type of information allows Chroma Manager to make intelligent selection of primary/secondary Lustre servers.

To express this information, create a HomingPreference resource which is a parent of the device node, and has as its
parent the LUN.
