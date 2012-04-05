
Chroma server user manual
=========================

This is a section about pieces of the UI
----------------------------------------

This is a subsection about the server list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. include:: contextual/server_list.rst

This is a section with additional non-contextual information
------------------------------------------------------------

.. _server_configuration

Server configuration
~~~~~~~~~~~~~~~~~~~~

When a Lustre server is added to Chroma, it is initially in an unconfigured state -- the
server is known only by an address that Chroma will try to contact to perform configuration.

During configuration, Chroma learns about the server:

* The server's LNet addresses
* The server's FQDN and node name


