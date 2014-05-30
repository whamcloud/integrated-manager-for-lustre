# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


from collections import defaultdict

import logging
import subprocess
from datetime import datetime, timedelta
import time
import argparse
from argparse import RawTextHelpFormatter
import os

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
handler = logging.FileHandler("chroma-diagnostics.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s',
                                       '%d/%b/%Y:%H:%M:%S'))
log.addHandler(handler)

# Dictionary of parent path to array of logfiles
# that are rolled by logrotated such that when rotated
# the current file copied with the extendion -<date>.gz
# and the file is gzipped.
logrotate_logs = {
    '/var/log/chroma/': ['job_scheduler.log',
                         'http.log',
                         'corosync.log',
                         'http_agent.log',
                         'lustre_audit.log',
                         'plugin_runner.log',
                         'power_control.log',
                         'stats.log',
                         'supervisord.log',
                         'install.log',
                         'client_errors.log',
                         'realtime.log',
                         ],
    '/var/log/httpd': ['error_log',
                       'access_log',
                       'ssl_error_log',
                       ],
    '/var/log/': ['messages',
                  'chroma-agent.log',
                  'chroma-agent-console.log'
                  ]}


def run_command(cmd, out, err):

    try:
        p = subprocess.Popen(cmd,
                             stdout = out,
                             stderr = err)
    except OSError:
        #  The cmd in this case could not run on this platform, skipping
#        log.info("Skipping: %s" % cmd)
        return None
    else:
        p.wait()
        try:
            out.flush()
        except AttributeError:
            # doesn't do flush
            pass
        try:
            err.flush()
        except AttributeError:
            # doesn't do flush
            pass
        return p


def dump(fn, cmd, output_directory):

    out_fn = "%s.out" % fn
    err_fn = "%s.err" % fn
    out_path = os.path.join(output_directory, out_fn)
    err_path = os.path.join(output_directory, err_fn)

    with open(out_path, 'w') as out:
        with open(err_path, 'w') as err:
            result = run_command(cmd, out, err)

    # Remove meaningless zero lenth error files
    if os.path.getsize(err_path) <= 0:
        os.remove(err_path)

    return result


def execute(cmd):
    return run_command(cmd, subprocess.PIPE, subprocess.PIPE)


def copy_logrotate_logs(output_directory, days_back=1, verbose=0):
    """Go days_back to find compressed logrotate.d type log files to be copied.

    Note:  Chose to use nieve dates here, since this will run on the same
    host that the file was created they are likely to match.  The server is
    probably in UTC anyway.
    """

    if days_back < 0:
        return 0

    # Create a cutoff date by step back from now the requested number of days
    # and then setting the time to the beginning of that day.
    # For example, if you run it as 3pm today, and ask for 1 day back, the
    # default you get a cut off of the beginning of the day yesterday all 24
    # hours of yesterday, up to right now, today.
    cutoff_date = datetime.now() - timedelta(days=days_back)
    cutoff_date = cutoff_date.replace(hour=0, minute=0, second=0)
    cutoff_date_seconds = time.mktime(cutoff_date.timetuple())

    collected_files = defaultdict(list)

    # Collect all suitable files
    for path, log_names_to_collect in logrotate_logs.items():
        if os.path.exists(path):
            for file_name in os.listdir(path):
                _dash = file_name.rfind('-')
                if _dash < 0 or not file_name.endswith('gz'):
                    # chroma-agent.log should be matched as a file_name
                    root_file_name = file_name
                else:
                    root_file_name = file_name[0:_dash]

                if root_file_name in log_names_to_collect:
                    abs_path = os.path.join(path, file_name)
                    last_modified = os.path.getmtime(abs_path)
                    if last_modified >= cutoff_date_seconds:
                        collected_files[root_file_name].append((abs_path,
                                                                last_modified))
        else:
            if verbose > 0:
                log.info("%s does not exist." % path)

    # Copy all files into one file per filename
    for file_name, log_files in collected_files.items():
        ordered_log_files = [t[0] for t in sorted(log_files,
                             key=lambda file_tuple: file_tuple[1])]
        output_file_name = os.path.join(output_directory, file_name)
        for log_file in ordered_log_files:
            if log_file.endswith('gz'):
                cmd = ['zcat', log_file, '>>', output_file_name, ]
            else:
                cmd = ['cat', log_file, '>>', output_file_name, ]
            subprocess.Popen(' '.join(cmd), shell=True)
        if verbose > 1:
            log.info("copied logs: " % "\t\n".join(ordered_log_files))

    return len(collected_files)

DEFAULT_OUTPUT_DIRECTORY = '/var/log/'

PACKAGES = ['chroma-agent',
            'chroma-agent-management',
            'chroma-manager',
            'chroma-manager-cli',
            'chroma-manager-libs']


def main():

    desc = ("Run this to save a tar-file collection of logs and diagnostic output.\n"
            "The tar-file created is compressed with lzma.\n"
            "Sample output:  %sdiagnostics_<date>_<fqdn>.tar.lzma"
            % DEFAULT_OUTPUT_DIRECTORY)

    parser = argparse.ArgumentParser(description=desc, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--verbose', '-v', action='count', required=False,
                        help="More output for troubleshooting.")

    def _check_days_back(arg):
        try:
            days_back = int(arg)
        except ValueError:
            msg = "%s is not a valid number of days."
            raise argparse.ArgumentTypeError(msg % arg)
        else:
            if days_back < 0:
                msg = "Number of days must not be less than zero."
                raise argparse.ArgumentTypeError(msg)
            else:
                return days_back
    parser.add_argument('--days-back', '-d', required=False,
                        type=_check_days_back, default=1,
                        help="Number of days back to collect logs. "
                             "default is 1.  0 would mean today's logs only.")
    args = parser.parse_args()

    time_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_fn = 'diagnostics_%s' % time_stamp

    hostname_process = execute(['hostname', '-f'])
    if hostname_process:
        output_fn = '%s_%s' % (output_fn, hostname_process.stdout.read().strip())

    output_directory = os.path.join(DEFAULT_OUTPUT_DIRECTORY, output_fn)
    os.mkdir(output_directory)

    log.info("\nCollecting diagnostic files\n")

    if dump('detected_devices', ['chroma-agent', 'device_plugin',
                                 '--plugin=linux'], output_directory):
        log.info("Detected devices")
    elif args.verbose > 0:
        log.info("Failed to Detected devices")

    if dump('rabbit_queue_status', ['rabbitmqctl', 'list_queues', '-p',
                                    'chromavhost'], output_directory):
        log.info("Inspected rabbit queues")
    elif args.verbose > 0:
        log.info("Failed to inspect rabbit queues")

    if dump('rpm_packges_installed', ['rpm', '-qa'], output_directory):
        log.info("Listed installed packages")
    elif args.verbose > 0:
        log.info("Failed to list installed packages")

    if dump('pacemaker-cib', ['cibadmin', '--query'], output_directory):
        log.info("Listed cibadmin --query")
    elif args.verbose > 0:
        log.info("Failed to list cibadmin --query")

    if dump('pacemaker-pcs-config-show', ['pcs', 'config', 'show'], output_directory):
        log.info("Listed: pcs config show")
    elif args.verbose > 0:
        log.info("Failed to list pcs config show")

    if dump('pacemaker-crm-mon-1', ['crm_mon', '-1r', ], output_directory):
        log.info("Listed: crm_mon -1r")
    elif args.verbose > 0:
        log.info("Failed to list crm_mon -1r")

    if dump('chroma-config-validate', ['chroma-config',
                                       'validate'], output_directory):
        log.info("Validated Intel Manager for Lustre® installation")
    elif args.verbose > 0:
        log.info("Failed to run Intel Manager for Lustre® installation validation")

    if dump('finger-print', ['rpm', '-V', ] + PACKAGES, output_directory):
        log.info("Finger printed Intel Manager for Lustre® installation")
    elif args.verbose > 0:
        log.info("Failed to finger print Intel Manager for Lustre® installation")

    if dump('ps', ['ps', '-ef', '--forest'], output_directory):
        log.info("Listed running processes")
    elif args.verbose > 0:
        log.info("Failed to list running processes: ps")

    if dump('lspci', ['lspci', '-v'], output_directory):
        log.info("listed PCI devices")
    elif args.verbose > 0:
        log.info("Failed to list PCI devices: lspci")

    if dump('df', ['df', '--all'], output_directory):
        log.info("listed file system disk space.")
    elif args.verbose > 0:
        log.info("Failed to list file system disk space : df")

    for proc in ['cpuinfo', 'meminfo', 'mounts', 'partitions']:
        if dump(proc, ['cat', '/proc/%s' % proc], output_directory):
            log.info("listed cat /proc/%s" % proc)
        elif args.verbose > 0:
            log.info("Failed to list cat /proc/%s" % proc)

    if dump('etc_hosts', ['cat', '/etc/hosts', ], output_directory):
        log.info("Listed hosts")
    elif args.verbose > 0:
        log.info("Failed to list hosts: /etc/hosts")

    log_count = copy_logrotate_logs(output_directory, args.days_back, args.verbose)
    if log_count > 0:
        log.info("Copied %s log files." % log_count)
    elif args.verbose > 0:
        log.info("Failed to copy logs")

    archive_path = '%s.tar.lzma' % output_directory
    #  Using -C to change to parent of dump dir,
    # then tar.lzma'ing just the output dir
    execute(['tar', '--lzma', '-cf', archive_path, '-C',
             DEFAULT_OUTPUT_DIRECTORY, output_fn])

    log.info("\nDiagnostic collection is completed.")
    log.info(archive_path)

    log.info(u"\nThe diagnostic report tar.lzma file can be "
             u"sent to Intel Manager for Lustre® Support for analysis.")


if __name__ == "__main__":
    main()
