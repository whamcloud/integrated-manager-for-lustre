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


import logging
import subprocess
from datetime import datetime, timedelta
import time
import argparse
import os

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
handler = logging.FileHandler("chroma-diagnostics.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
log.addHandler(handler)

# Filenames included
# if a log file in the directory (key) starts with any string in the list (value)
# then include the log.  This is used below to match rolled over copies of the
# logs
tracked_logs = {'/var/log/chroma/': ['chroma-agent',
                                     'chroma-agent-console',
                                     'chroma-agent-daemon',
                                     'job_scheduler',
                                     'http',
                                     'corosync',
                                     'http_agent',
                                     'lustre_audit',
                                     'messages',
                                     'plugin_runner',
                                     'power_control',
                                     'stats',
                                     'supervisord', ],
                '/var/log/': ['syslog',
                              'messages',
                              'system', ]}


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
            return run_command(cmd, out, err)


def execute(cmd):
    return run_command(cmd, subprocess.PIPE, subprocess.PIPE)


def copy_logs(output_directory, days_back=1, verbose=0):
    """Go days_back to find logs files to be copied.

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

    collected_files = []

    # Consider each log path
    for path, file_roots in tracked_logs.items():
        if os.path.exists(path):
            for file in os.listdir(path):
                file_root = file.split('.')[0]
                valid_name = file_root in file_roots
                if valid_name:
                    abs_path = os.path.join(path, file)
                    last_modified = os.path.getmtime(abs_path)
                    if last_modified >= cutoff_date_seconds:
                        collected_files.append(abs_path)
        else:
            if verbose > 0:
                log.info("%s does not exist." % path)

    if verbose > 1:
        log.info("Copy %s" % "\t\n".join(collected_files))

    execute(['cp', ] + collected_files + [output_directory, ])
    return len(collected_files)

DEFAULT_OUTPUT_DIRECTORY = '/var/log/'

PACKAGES = ['chroma-agent',
            'chroma-agent-management',
            'chroma-manager',
            'chroma-manager-cli',
            'chroma-manager-libs']


def main():

    desc = ("Run this save a tar gzipped collection of "
            "logs and diagnostic output.  "
            "Output:  %sdiagnostics_<date>_<fqdn>.tar.gz"
            % DEFAULT_OUTPUT_DIRECTORY)

    parser = argparse.ArgumentParser(description=desc)
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
        type=_check_days_back,
        default=1, help="Number of days back to collect logs. default is 1.  0 "
                        "would mean today's logs only.")
    args = parser.parse_args()

    time_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_fn = 'diagnostics_%s' % time_stamp

    hostname_process = execute(['hostname', '-f'])
    if hostname_process:
        output_fn = '%s_%s' % (output_fn, hostname_process.stdout.read().strip())

    output_directory = os.path.join(DEFAULT_OUTPUT_DIRECTORY, output_fn)
    os.mkdir(output_directory)

    log.info("\nCollecting diagnostic files\n")

    if dump('detected_devices.dump',
        ['chroma-agent', 'device_plugin', '--plugin=linux'], output_directory):
        log.info("Detected devices")
    elif args.verbose > 0:
        log.info("Failed to Detected devices")

    if dump('rabbit_queue_status.dump',
        ['rabbitmqctl', 'list_queues', '-p', 'chromavhost'], output_directory):
        log.info("Inspected rabbit queues")
    elif args.verbose > 0:
        log.info("Failed to inspect rabbit queues")

    if dump('rpm_packges_installed.dump', ['rpm', '-qa'], output_directory):
        log.info("Listed installed packages")
    elif args.verbose > 0:
        log.info("Failed to list installed packages")

    if dump('pacemaker-cib.dump', ['cibadmin', '--query'], output_directory):
        log.info("Listed pacemaker configuration")
    elif args.verbose > 0:
        log.info("Failed to list Pacemaker configuration")

    if dump('chroma-config-validate.dump', ['chroma-config', 'validate'], output_directory):
        log.info("Validated chroma installation")
    elif args.verbose > 0:
        log.info("Failed to run chroma installation validation")

    if dump('finger-print.dump', ['rpm', '-V', ] + PACKAGES, output_directory):
        log.info("Finger printed chroma installation")
    elif args.verbose > 0:
        log.info("Failed to finger print chroma installation")

    log_count = copy_logs(output_directory, args.days_back, args.verbose)
    if log_count > 0:
        log.info("Copied %s log files." % log_count)
    elif args.verbose > 0:
        log.info("Failed to copy logs")

    tgz_path = '%s.tar.gz' % output_directory
    #  Using -C to change to parent of dump dir, then tgz'ing just the output dir
    execute(['tar', '-czf', tgz_path, '-C', DEFAULT_OUTPUT_DIRECTORY, output_fn])

    log.info("\nDiagnostic collection is completed.")
    log.info(tgz_path)

    log.info("\nThe diagnostic report tgz file can be "
             "emailed to Chroma support for analysis.")


if __name__ == "__main__":
    main()
