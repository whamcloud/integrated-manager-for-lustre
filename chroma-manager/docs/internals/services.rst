
Chroma Manager backend infrastructure
=====================================

Long-running threads are declared as services, subclassing `ChromaService`.  The purpose of 
having this class rather than just having each service operate as a standalone script is to
decouple the definition of services from the definition of the processes that contain 
services.  Practically, that means that the services can be run in a number of 
separate processes (a number hopefully similar to the number of cores), or many
services can be run within a single process (useful for test and development).

The `chroma_service` management command is used for starting one or more services in a
new process.

To add a service to Chroma, create a module under chroma_core.services, and within the module
define a class named `Service` which subclasses `ChromaService`.

ChromaService
-------------

.. autoclass:: chroma_core.services.ChromaService


Logging
-------

.. automodule:: chroma_core.services.log
    :members:


ServiceThread
-------------
.. autoclass:: chroma_core.services.ServiceThread


RPC
---


RPC interface
_____________

.. autoclass:: chroma_core.services.rpc.ServiceRpcInterface

RPC internals
_____________

.. autoclass:: chroma_core.services.rpc.RpcClient

.. autoclass:: chroma_core.services.rpc.RpcClientFactory

.. autoclass:: chroma_core.services.rpc.RpcClientResponseHandler

.. autoclass:: chroma_core.services.rpc.RpcServer

.. autoclass:: chroma_core.services.rpc.RunOneRpc



Queues
------

.. automodule:: chroma_core.services.queue

.. autoclass:: chroma_core.services.queue.ServiceQueue
