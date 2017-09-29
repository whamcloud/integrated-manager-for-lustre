# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple


PACKAGES = ['chroma-agent',
            'chroma-agent-management',
            'chroma-manager',
            'chroma-manager-cli',
            'chroma-manager-libs']

# Dictionary of parent path to array of logfiles
# that are rolled by logrotated such that when rotated
# the current file is copied, gzipped and renamed
# with the extention "-<date>.gz"


CDAction = namedtuple(
    'CDAction', ['log_filename', 'cmd', 'cmd_desc', 'error_message', 'in_sos'])

detected_devices_action = CDAction('detected_devices',
                                   ['chroma-agent', 'device_plugin',
                                       '--plugin=linux'],
                                   "Detected devices",
                                   "Failed to detect Linux system devices",
                                   False)

monitored_devices_action = CDAction('monitored_devices',
                                    ['chroma-agent', 'detect_scan'],
                                    "Devices monitored",
                                    "Failed to detect devices containing Lustre components",
                                    False)

rabbit_queue_action = CDAction('rabbit_queue_status',
                               ['rabbitmqctl', 'list_queues', '-p', 'chromavhost'],
                               "Inspected rabbit queues",
                               "Failed to inspect rabbit queues",
                               True)

rpm_packges_installed_action = CDAction('rpm_packges_installed',
                                        ['rpm', '-qa'],
                                        "Listed installed packages",
                                        "Failed to list installed packages",
                                        True)

pacemaker_cib_action = CDAction('pacemaker-cib',
                                ['cibadmin', '--query'],
                                "Listed cibadmin --query",
                                "Failed to list cibadmin --query",
                                False)

pacemaker_pcs_action = CDAction('pacemaker-pcs-config-show',
                                ['pcs', 'config', 'show'],
                                "Listed: pcs config show",
                                "Failed to list pcs config show",
                                False)

pacemaker_crm_action = CDAction('pacemaker-crm-mon-1',
                                ['crm_mon', '-1r', ],
                                "Listed: crm_mon -1r",
                                "Failed to list crm_mon -1r",
                                False)

chroma_config_action = CDAction('chroma-config-validate',
                                ['chroma-config', 'validate'],
                                "Validated Intel® Manager for Lustre* software installation",
                                "Failed to run Intel® Manager for Lustre* software installation validation",
                                False)

finger_print_action = CDAction('finger-print',
                               ['rpm', '-V', ] + PACKAGES,
                               "Finger printed Intel® Manager for Lustre* software installation",
                               "Failed to finger print Intel® Manager for Lustre* software installation",
                               False)

ps_action = CDAction('ps',
                     ['ps', '-ef', '--forest'],
                     "Listed running processes",
                     "Failed to list running processes: ps",
                     False)

lspci_action = CDAction('lspci',
                        ['lspci', '-v'],
                        "listed PCI devices",
                        "Failed to list PCI devices: lspci",
                        True)

df_action = CDAction('df',
                     ['df', '--all'],
                     "listed file system disk space.",
                     "Failed to list file system disk space : df",
                     True)

etc_hosts_action = CDAction('/etc/hosts',
                            ['cat', '/etc/hosts', ],
                            "Listed hosts",
                            "Failed to list hosts: /etc/hosts",
                            True)

blk_action = CDAction('blk',
                      ['blkid', '-s', 'UUID', '-s', 'TYPE'],
                      "Listed devices that contain a filesystem",
                      "Failed to list devices that contain a filesystem",
                      False)

network_scan_action = CDAction('network_scan',
                               ['chroma-agent', 'device_plugin',
                                   '--plugin=linux_network'],
                               "Network scan information",
                               "Failed to list network information",
                               False)

sysctl_action = CDAction('sysctl',
                         ['sysctl', '-a'],
                         "list of kernel settings configurable in /proc/sys/",
                         "Failed to list kernal settings configurable in /proc/sys/",
                         True)

lctl_devices_action = CDAction('lctl_devices',
                               ['lctl', 'device_list'],
                               "List of Lustre devices",
                               "Failed to list Lustre Devices",
                               False)

lctl_debug_kernal_action = CDAction('lctl_kernel',
                                    ['lctl', 'debug_kernel'],
                                    "listed debug kernel ouput",
                                    "Failed to list kernel output",
                                    False)

proc_actions = [CDAction('proc',
                         ['cat', '/proc/%s' % proc],
                         "listed cat /proc/%s" % proc,
                         "Failed to list cat /proc/%s" % proc,
                         True)
                for proc in ['cpuinfo', 'meminfo', 'mounts',
                             'partitions']]


def cd_actions(exclude_actions_in_sos):

    all_actions = [detected_devices_action,
                   monitored_devices_action,
                   rabbit_queue_action,
                   rpm_packges_installed_action,
                   pacemaker_cib_action,
                   pacemaker_pcs_action,
                   pacemaker_crm_action,
                   chroma_config_action,
                   finger_print_action,
                   ps_action,
                   lspci_action,
                   df_action,
                   etc_hosts_action,
                   blk_action,
                   network_scan_action,
                   sysctl_action,
                   lctl_debug_kernal_action,
                   lctl_devices_action] + proc_actions

    # Return action if the action command isnt in sosreport or if sosreport is not going to run
    return [action for action in all_actions if (action.in_sos is False) or (exclude_actions_in_sos is False)]
