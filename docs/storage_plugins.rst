
Chroma storage plugin developer's guide
=======================================

Introduction
------------

Declaring StorageResources
--------------------------

A `StorageResource` represents a single, uniquely identified object.  It may be a physical
device such as a physical hard drive, or a virtual object such as a storage pool or 
virtual machine.

.. code-block:: python

   from configure.lib.storage_plugin.resource import StorageResource, GlobalId

   class HardDrive(StorageResource):
       serial_number = attributes.String()
       capacity = attributes.Bytes()

       identifier = GlobalId('serial_number')

Declaring a ScannableStorageResource
------------------------------------

Implementing StoragePlugin
--------------------------

.. automodule:: configure.lib.storage_plugin
.. autoclass:: configure.lib.storage_plugin.plugin.StoragePlugin
  :members:

.. autoclass:: configure.lib.storage_plugin.resource.StorageResource
  :members:

Running a plugin in development
-------------------------------

Before starting, you should already have a hydra-server development instance set up.

Advanced: special storage resources
-----------------------------------


Reference: attribute classes
----------------------------

.. automodule:: configure.lib.storage_plugin.attributes
   :members:

Reference: statistic classes
----------------------------

.. automodule:: configure.lib.storage_plugin.statistics
   :members:

Reference: built-in resource classes
------------------------------------

.. automodule:: configure.lib.storage_plugin.base_resources
   :members:
