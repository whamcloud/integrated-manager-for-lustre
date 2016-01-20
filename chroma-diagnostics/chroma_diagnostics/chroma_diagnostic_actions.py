#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


CDAction = namedtuple('CDAction', ['log_filename', 'cmd', 'cmd_desc', 'error_message'])

detected_devices_action = CDAction('detected_devices',
                                   ['chroma-agent', 'device_plugin', '--plugin=linux'],
                                   "Detected devices",
                                   "Failed to detect Linux system devices")

monitored_devices_action = CDAction('monitored_devices',
                                    ['chroma-agent', 'detect_scan'],
                                    "Devices monitored",
                                    "Failed to detect devices containing Lustre components")

rabbit_queue_action = CDAction('rabbit_queue_status',
                               ['rabbitmqctl', 'list_queues', '-p', 'chromavhost'],
                               "Inspected rabbit queues",
                               "Failed to inspect rabbit queues")

rpm_packges_installed_action = CDAction('rpm_packges_installed',
                                        ['rpm', '-qa'],
                                        "Listed installed packages",
                                        "Failed to list installed packages")

pacemaker_cib_action = CDAction('pacemaker-cib',
                                ['cibadmin', '--query'],
                                "Listed cibadmin --query",
                                "Failed to list cibadmin --query")

pacemaker_pcs_action = CDAction('pacemaker-pcs-config-show',
                                ['pcs', 'config', 'show'],
                                "Listed: pcs config show",
                                "Failed to list pcs config show")

pacemaker_crm_action = CDAction('pacemaker-crm-mon-1',
                                ['crm_mon', '-1r', ],
                                "Listed: crm_mon -1r",
                                "Failed to list crm_mon -1r")

chroma_config_action = CDAction('chroma-config-validate',
                                ['chroma-config', 'validate'],
                                "Validated Intel Manager for Lustre installation",
                                "Failed to run Intel Manager for Lustre installation validation")

finger_print_action = CDAction('finger-print',
                               ['rpm', '-V', ] + PACKAGES,
                               "Finger printed Intel Manager for Lustre installation",
                               "Failed to finger print Intel Manager for Lustre installation")

ps_action = CDAction('ps',
                     ['ps', '-ef', '--forest'],
                     "Listed running processes",
                     "Failed to list running processes: ps")

lspci_action = CDAction('lspci',
                        ['lspci', '-v'],
                        "listed PCI devices",
                        "Failed to list PCI devices: lspci")

df_action = CDAction('df',
                     ['df', '--all'],
                     "listed file system disk space.",
                     "Failed to list file system disk space : df")

etc_hosts_action = CDAction('/etc/hosts',
                            ['cat', '/etc/hosts', ],
                            "Listed hosts",
                            "Failed to list hosts: /etc/hosts")

blk_action = CDAction('blk',
                      ['blkid', '-s', 'UUID', '-s', 'TYPE'],
                      "Listed devices that contain a filesystem",
                      "Failed to list devices that contain a filesystem")

network_scan_action = CDAction('network_scan',
                               ['chroma-agent', 'device_plugin', '--plugin=linux_network'],
                               "Network scan information",
                               "Failed to list network information")

sysctl_action = CDAction('sysctl',
                         ['sysctl', '-a'],
                         "list of kernel settings configurable in /proc/sys/",
                         "Failed to list kernal settings configurable in /proc/sys/")

proc_actions = [CDAction('proc',
                         ['cat', '/proc/%s' % proc],
                         "listed cat /proc/%s" % proc,
                         "Failed to list cat /proc/%s" % proc)
                for proc in ['cpuinfo', 'meminfo', 'mounts', 'partitions']]


def cd_actions():

    return [detected_devices_action,
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
            proc_actions]
