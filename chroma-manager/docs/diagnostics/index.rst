chroma-diagnostics
------------------

The diagnostics can run on any Chroma server, either the manager or a storage node.  This
utility provides a way to collect specific data from a system to aid in diagnosing problems.


chroma_diagnostics utility
__________________________

*chroma-diagnostics* is a commandline command.  Run it with no arguments to produce a
directory, in /var/log/, containing a collection of diagnostic files.  The directory
is named as follows:

/var/log/diagnostic_report_<datetime>


Files in directory
__________________

detected_devices.dump -  List of devices as detected
rabbit_queue_status.dump - Status of Rabbitmq queues
rpm_packges_installed.dump - RPM packages installed
pacemaker-cib.dump - The packmaker configuration
chroma-config-validate.dump - Chroma validation output

Including various application and system logs copied.
