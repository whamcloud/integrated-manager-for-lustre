#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


help_text = {
    'advanced_settings': '<b>Use care when changing these parameters as they can significantly impact functionality or performance.</b> For help with these settings, contact your storage solution provider.',
    'bytes_per_inode': 'File system space (in bytes) per MDS inode. The default is 2048, meaning one MDS inode per each 2048 bytes of file system space. In the "Lustre Operations Manual", see Section 5.3.3: Setting the Number of Inodes for the MDS.',
    'commands': 'Shows past and currently running commands that the manager is executing to perform tasks, such as formatting or starting a file system.',
    'command_detail': 'View details about this command.',
    'detect_file_systems-dialog': 'Ensure that all storage servers for mounted Lustre targets in the file system to be detected are up and running. Then select the storage servers (including passive failover servers) and click <b>Run</b> to scan them for existing Lustre targets.',
    'dismiss_message': 'Acknowledge this message and move it to the history view.',
    'goto_dashboard': 'Go to the Dashboard',
    'detect_file_systems-tooltip': 'Detect an existing file system to be monitored at the manager GUI.',
    'inode_size': 'Size (in bytes) of the inodes used to store Lustre metadata on the MDS for each file. The default is 512 bytes. In the "Lustre Operations Manual", see 5.3.1: Setting the Number of Inodes for the MDS.',
    'force_remove': 'This action removes the record for the storage server in the manager database, without attempting to contact the storage server. All targets that depend on this server will also be removed without any attempt to unconfigure them.  <b>You should only perform this action if the server is permanently unavailable.</b>',
    'invoke_agent': 'Indicates that the chroma-agent service can be accessed on this server.',
    'last_contact': 'The time that the manager GUI last received a status update from this server.',
    'nids': 'The Lustre network identifier(s) for the LNet network(s) to which this node belongs.',
    'ping': 'Indicates if an ICMP ping from the server running Intel(R) Manager for Lustre, to the server, succeeded.',
    'type': 'The type of storage device.',

    'rescan_NIDs-dialog': 'Select all servers for which the server NID may have changed and click <b>Run</b> to re-read the NIDs. <i>Note:</i> After completing this operation, you must update any affected Lustre targets by clicking the <strong>Re-write Target Configuration</strong> button.',
    'remove_server': 'Remove this server. Any file systems or targets that rely on this server will also be removed.',
    'rescan_NIDs-tooltip': 'Query the network interfaces on the storage servers to update the record of NIDs.',
    'reverse_ping': 'Indicates if an ICMP ping from the storage server to manager server succeeded.',
    'resolve': 'Indicates if a DNS lookup performed at the manager server, of the fully-qualified domain name (FQDN) of the storage server, succeeded.',
    'reverse_resolve': 'Indicates if a DNS lookup by the storage server of the fully-qualified domain name (FQDN) of the manager server succeeded.',

    'rewrite_target_configuration-dialog': 'Select all servers for which the NIDs were re-read by clicking the <strong>Rescan NIDs</strong> button.  Then click <b>Run</b> to rewrite the Lustre target configuration for targets associated with the selected servers.',
    'rewrite_target_configuration-tooltip': 'Update each target with the current NID for the server with which it is associated.',

    'server_status_configured': 'This server has been configured for use with the manager GUI.',
    'server_status_lnet_down': 'The LNet kernel module is loaded, but LNet networking is not currently started on this server.',
    'server_status_lnet_unloaded': 'The LNet kernel module is not currently loaded on this server.',
    'server_status_lnet_up': 'LNet networking is started on this server.',
    'server_status_unconfigured': 'This server has not yet been configured for use with the manager GUI.',

    'state_changed': 'Time at which the state last changed, either detected or as a result of user action.',

    'status': 'Indicates the status of high availability (HA) configuration for this volume (ha = available for HA, noha = not configured for HA).',
    'status_light': 'Indicates current system health. <br /> Green: The file system is operating normally. <br />  Yellow: The system may be operating in a degraded mode. <br /> Red: This system may be down or is severely degraded. <br /> Click to view all system event and alert status messages.',

    'start_file_system': 'Start the metadata and object storage targets so the file system can be mounted by clients.,',
    'stop_file_system': 'Stop the metadata and object storage targets, thus making the file system unavailable to clients.',
    'remove_file_system': 'Remove file system. This file system\'s contents will remain intact until its volumes are reused in another file system.',

    'lnet_state': 'The status of the LNet networking layer on this server.',
    'start_lnet': 'Load the LNet kernel module and start the LNet networking layer.',
    'stop_lnet': 'Shut down the LNet networking layer and stop any targets running on this server.',
    'unload_lnet': 'If LNet is running, stop LNET and unload the LNet kernel module to ensure that it will be reloaded before any targets are started again.',

    'start_mdt': 'Start the metadata target (MDT).',
    'stop_mdt': 'Stop the MDT. When an MDT is stopped, the file system becomes unavailable until the MDT is started again. If an object reference is known to a client, the client can continue to access the object in the file system after the MDT is shut down, but will not be able to obtain new object references.',

    'start_mgt': 'Start the management target (MGT).',
    'stop_mgt': 'Stop the MGT. When an MGT is stopped, clients are unable to make new connections to file systems using the MGT. However, MDT(s) and OST(s) stay up if they have been started and can be stopped and restarted while the MGT is stopped.',
    'remove_mgt': 'Remove this MGT. The contents will remain intact until the volume is reused for a new target.',

    'start_ost': 'Start the object storage target (OST).',
    'stop_ost': 'Stop the OST. When an OST is stopped, clients are unable to access the files stored on this OST.',
    'remove_ost': 'Remove the OST from the file system. This OST will no longer be seen in the manager GUI. <strong>Caution</strong>: When an OST is removed, files stored on the OST will no longer be accessible.<b> To preserve data, manually create a copy of the data elsewhere before removing the OST.</b>',

    'volume_long': 'Volumes (also called LUNs or block devices) are the underlying units of storage used to create Lustre file systems.  Each Lustre target corresponds to a single volume. If servers in the volume have been configured for high availability, primary and secondary servers can be designated for a Lustre target. Only volumes that are not already in use as Lustre targets or local file systems are shown. A volume may be accessible on one or more servers via different device nodes, and it may be accessible via multiple device nodes on the same host.',
    'volume_short': 'A LUN or block device used as a metadata or object storage target in a Lustre file system.',
    'volume_status_configured-ha': 'This volume is ready to be used for a high-availability (HA) Lustre target.',
    'volume_status_configured-noha': 'This volume is ready to be used as a Lustre target, but is not configured for high availability.',
    'volume_status_unconfigured': 'This volume cannot be used as a Lustre target until a primary server is selected.',
}
