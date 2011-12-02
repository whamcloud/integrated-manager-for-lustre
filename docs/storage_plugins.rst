
Chroma storage plugin developer's guide
=======================================

Introduction
------------

Within Chroma, storage plugins are responsible for delivering information about
entities which are not part of the Linux/Lustre stack.  This primarily means
storage controllers and network devices, but the plugin system is generic and 
does not limit the type of objects that can be reported.

Plugins are written in Python and loaded into Chroma at runtime.

The aim of this API is to minimize the lines of code required to write a plugin, 
minimize the duplication of effort between different plugins, and make as much
of the plugin code as possible declarative in style to minimize the need for 
per-plugin testing.  For example, rather than having plugin authors procedurally
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


Declaring StorageResources
--------------------------

A `StorageResource` represents a single, uniquely identified object.  It may be a physical
device such as a physical hard drive, or a virtual object such as a storage pool or 
virtual machine.

.. code-block:: python

   from configure.lib.storage_plugin.resource import StorageResource, GlobalId
   from configure.lib.storage_plugin import attributes, statistics

   class HardDrive(StorageResource):
       serial_number = attributes.String()
       capacity = attributes.Bytes()
       temperature = statistics.Gauge(units = 'C')

       identifier = GlobalId('serial_number')

Attributes
~~~~~~~~~~

The ``serial_number`` and ``capacity`` attributes of the HardDrive class are
StorageResourceAttributes.  These are special classes which:

* apply validation conditions to the attributes
* act as metadata for the presentation of the attribute in the user interface

Various attribute classes are available for use, see :ref:`storage_plugin_attribute_classes`.

Statistics
~~~~~~~~~~

The ``temperature`` attribute of the HardDrive class is an example of
a StorageResourceStatistic.  Resource statistics differ from resource
attributes in the way they are presented to the user.  See :ref:`storage_plugin_statistic_classes`
for more on statistics.

Identifiers
~~~~~~~~~~~

Every StorageResource subclass is required to have an ``identifier`` attribute
which declares which attributes are to be used to uniquely identify the resource.

If a resource has a universally unique name and may be reported from more than one
place (for example, a physical disk which might be reported from more than one 
controller), use ``configure.lib.storage_plugin.resource.GlobalId``.  This is the
case for the example ``HardDrive`` class above, which has a factory-assigned ID 
for the drive.

If a resource has an identifier which is scoped to a *scannable* storage resource or
it always belongs to a particular scannable storage resource, then use
``configure.lib.storage_plugin.resource.ScannableId``.

Either of the above classes is initialized with a list of attributes which
in combination are a unique identifier.  For example, if a true hard drive 
identifier was unavailable, a drive might be identified within a particular couplet 
by its shelf and slot number, like this:
::

    class HardDrive(StorageResource):
        shelf = attributes.ResourceReference()
        slot = attributes.Integer()
        identifier = ScannableId('shelf', 'slot')

Declaring a ScannableStorageResource
------------------------------------

Certain storage resources are considered 'scannable':
* They can be added by the administrator using the user interface
* Plugins contact this resource to learn about other resources
* This resource 'owns' some other resources

The archetypal scannable resource is a storage controller or couplet of
storage controllers.

::

   from configure.lib.storage_plugin.resource import ScannableStorageResource, GlobalId

   class StorageController(StorageResource):
       address_1 = attributes.Hostname()
       address_2 = attributes.Hostname()

       identifier = GlobalId('address_1', 'address_2')

Implementing StoragePlugin
--------------------------

The StorageResource classes are simply declarations of what resources can be 
reported by the plugin, and what properties they will have.  The plugin module
must also contain a subclass of *StoragePlugin* which implements at least the
``initial_scan`` function:

.. automethod:: configure.lib.storage_plugin.plugin.StoragePlugin.initial_scan

Within ``initial_scan``, plugins use the ``update_or_create`` function to 
report resources.

.. automethod:: configure.lib.storage_plugin.plugin.StoragePlugin.update_or_create

If any resources are allocated in ``initial_scan``, such as threads or 
sockets, they may be freed in the ``teardown`` function:

.. automethod:: configure.lib.storage_plugin.plugin.StoragePlugin.teardown

After initialization, the ``update_scan`` function will be called periodically.
You can set the delay between ``update_scan`` calls by assigning to
``self.update_period`` before leaving in ``initial_scan``.  Assignments to
``update_period`` after ``initial_scan`` will have no effect.

.. automethod:: configure.lib.storage_plugin.plugin.StoragePlugin.update_scan

If a resource has changed, you can either use ``update_or_create`` to modify 
attributes or parent relationships, or you can directly assign to the resource's 
attributes, or use its add_parent and remove_parent functions.  If a resource has 
gone away, use ``remove`` to notify Chroma:

.. automethod:: configure.lib.storage_plugin.plugin.StoragePlugin.remove

Although resources must be reported synchronously during ``initial_scan``, this
is not the case for updates.  For example, if a storage device provides asynchronous
updates via a network protocol, the plugin author may spawn a thread in ``initial_scan``
which listens for these updates.  The thread listening for updates may modify resources
and make ``update_or_create`` and ``remove`` calls on the plugin object.
Plugins written in this way would probably not implement ``update_scan`` at all.


Running a plugin in development
-------------------------------


Advanced: special storage resources
-----------------------------------

Certain of the :ref:`storage_plugin_builtin_resource_classes` have special behaviours:

Advanced: linking up resources using ``provide``
------------------------------------------------

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

Reference
=========

.. _storage_plugin_attribute_classes:

Attribute classes
----------------------------

.. automodule:: configure.lib.storage_plugin.attributes
   :members:

.. _storage_plugin_statistic_classes:

Statistic classes
----------------------------

.. automodule:: configure.lib.storage_plugin.statistics
   :members:

.. _storage_plugin_builtin_resource_classes:

Built-in resource classes
------------------------------------

.. automodule:: configure.lib.storage_plugin.base_resources
   :members:
