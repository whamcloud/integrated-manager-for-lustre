
This is some contextual help about the server list.  For example, I'm
going to tell the user what the columns mean:

name
  The fully qualified domain name of the server, if it is configured, otherwise
  the address of the server if it has been added but not yet configured by Chroma.
  In many cases the FQDN and address are the same, e.g. 'myhost' might be both, but 
  the address might be 'myhost:22' and the FQDN might be 'myhost.mycompany'.  See
  :ref:`server_configuration` for more information about addresses vs. FQDNs.

LNet status
  The state of the LNet layer on this host.  This can be unloaded (the LNet module
  is not loaded), stopped (the LNet module is loaded but interfaces have not been
  started) or started (LNet is online and ready for use).

