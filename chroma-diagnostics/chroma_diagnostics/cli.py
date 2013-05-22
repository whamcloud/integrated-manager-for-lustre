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
from datetime import datetime
import argparse
import os

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
handler = logging.FileHandler("chroma-diagnostics.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
log.addHandler(handler)

chroma_log_locations = ['/var/log/chroma-agent.log',
                 '/var/log/chroma-agent-console.log',
                 '/var/log/chroma-agent-daemon.log',
                 '/var/log/chroma/job_scheduler.log',
                 '/var/log/chroma/http.log',
                 '/var/log/chroma/corosync.log',
                 '/var/log/chroma/http_agent.log',
                 '/var/log/chroma/lustre_audit.log',
                 '/var/log/chroma/messages',
                 '/var/log/chroma/plugin_runner.log',
                 '/var/log/chroma/power_control.log',
                 '/var/log/chroma/stats.log',
                 '/var/log/chroma/supervisord.log',
                 '/var/log/syslog.log', ]


def run_command(cmd, out, err):

    try:
        p = subprocess.Popen(cmd,
            stdout = out,
            stderr = err)
    except OSError:
        #  The cmd in this case could not run on this platform, skipping
        log.debug("Skipping: %s" % cmd)
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


DEFAULT_OUTPUT_DIRECTORY = '/var/log/'


def main():

    desc = ("Run this save a tar gzipped collection of "
            "logs and diagnostic output.  "
            "Output:  %sdiagnostics_<date>_<fqdn>.tar.gz"
            % DEFAULT_OUTPUT_DIRECTORY)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--verbose', '-v', action='count')
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

    if execute(['cp', ] + chroma_log_locations + [output_directory, ]):
        log.info("Copied all log files")
    elif args.verbose > 0:
        log.info("Failed to copy logs")

    tgz_path = '%s.tar.gz' % output_directory
    #  Using -C to change to parent of dump dir, then tgz'ing just the output dir
    execute(['tar', '-czf', tgz_path, '-C', DEFAULT_OUTPUT_DIRECTORY, output_fn])

    log.info("\nDiagnostic collection is completed.")
    log.info(tgz_path)

    log.info("\nThe diagnostic report tgz file can be "
             "emailed to Chroma support for analysis.")
