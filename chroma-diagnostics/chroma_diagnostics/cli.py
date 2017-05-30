# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
import socket
import logging
import subprocess
from datetime import datetime, timedelta
import time
import argparse
from argparse import RawTextHelpFormatter
import os
import sys

from chroma_diagnostic_actions import cd_actions

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
handler = logging.FileHandler("chroma-diagnostics.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
log.addHandler(handler)

DEFAULT_OUTPUT_DIRECTORY = '/var/log/'
# Always exclude these tables from DB output
EXCLUDED_TABLES = ['chroma_core_logmessage', 'chroma_core_series', 'chroma_core_sample_*']

# Dictionary of parent path to array of logfiles
# that are rolled by logrotated such that when rotated
# the current file is copied, gzipped and renamed
# with the extention "-<date>.gz"
logrotate_logs = {
    '/var/log/chroma/': [],
    '/var/log/nginx': ['error.log',
                       'access.log'
                       ],
    '/var/log/': ['messages',
                  'chroma-agent.log',
                  'chroma-agent-console.log'
                  ]}


def run_command(cmd, out, err):

    try:
        p = subprocess.Popen(cmd, stdout = out, stderr = err)
    except OSError:
        #  The cmd in this case could not run, skipping
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


def run_command_output_piped(cmd):
    return run_command(cmd, subprocess.PIPE, subprocess.PIPE)


def save_command_output(fn, cmd, output_directory):

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


def copy_logrotate_logs(output_directory, days_back=1, verbose=0):
    """Go days_back to find compressed logrotate.d type log files to be copied.

    Note:  Chose to use naive dates here, since this will run on the same
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
            if log_names_to_collect == []:
                for log_file in os.listdir(path):
                    if log_file.endswith(".log"):
                        log_names_to_collect.append(log_file)
            for file_name in os.listdir(path):
                _dash = file_name.rfind('-')
                if _dash < 0 or not file_name.endswith('gz'):
                    # chroma-agent.log should be matched as a file_name
                    root_file_name = file_name
                else:
                    root_file_name = file_name[0:_dash]

                if root_file_name in log_names_to_collect:
                    abs_path = os.path.join(path, file_name)
                    if verbose > 2:
                        log.info(run_command_output_piped(['ls', '-l', abs_path]).stdout.read())
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
                                                  key=lambda file_tuple:
                                                  file_tuple[1])]
        output_file_name = os.path.join(output_directory, file_name)
        for log_file in ordered_log_files:
            if log_file.endswith('gz'):
                cmd = ['zcat', log_file, '>>', output_file_name, ]
            else:
                cmd = ['cat', log_file, '>>', output_file_name, ]
            subprocess.Popen(' '.join(cmd), shell=True)
        if verbose > 1:
            log.info("copied logs: %s" % "\t\n".join(ordered_log_files))

    return len(collected_files)


def export_postgres_chroma_db(parent_directory):

    # export db in plantext, compressed (gzip), and never ask for password
    time_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_fn = 'chromadb_%s' % time_stamp
    output_path = os.path.join(parent_directory, '%s.sql.gz' % output_fn)

    #  Dump and compress to a file ...
    cmd_export = ['pg_dump', '-U', 'chroma', '-F', 'p', '-Z', '9', '-w', '-f', output_path]

    #  ... while excluding tables
    cmd_export += sum([['-T', table_name] for table_name in EXCLUDED_TABLES], [])

    # ... the IML database
    cmd_export += ['chroma']

    return run_command_output_piped(cmd_export)


def change_tree_permissions(root_directory, new_permission):
    """Change the permissions of all the files and directories below and
    including the root_directory passed.
    root_directory: Root to directory tree to change permissions of.
    new_permission: Permission value to set.
    """
    for root, dirs, files in os.walk(root_directory):
        for cd_file in files:
            path = os.path.join(root, cd_file)
            if os.path.exists(path):
                os.chmod(os.path.join(root, cd_file), new_permission)


def main():

    default_output_directory = DEFAULT_OUTPUT_DIRECTORY

    desc = ("Run this to save a tar-file collection of logs and diagnostic output.\n"
            "The tar-file created is compressed with lzma.\n"
            "Sample output:  %sdiagnostics_<date>_<fqdn>.tar.lzma"
            % default_output_directory)

    parser = argparse.ArgumentParser(description=desc, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--alt-dir', '-a', action='store', dest='directory', type=basestring, required=False,
                        help="Specify output location for diagnostics.")

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

    output_fn = 'diagnostics_%s_%s' % (socket.gethostname(),
                                       datetime.now().strftime("%Y%m%dT%H%M%S"))

    if args.directory:
        default_output_directory = args.directory

    output_directory = os.path.join(default_output_directory, output_fn)
    os.mkdir(output_directory)

    log.info("\nCollecting diagnostic files\n")
    run_sos = args.verbose > 0
    for cd_action in cd_actions(run_sos):
        if save_command_output(cd_action.log_filename, cd_action.cmd, output_directory):
            log.info(cd_action.cmd_desc)
        elif args.verbose > 0:
            log.info(cd_action.error_message)

    log_count = copy_logrotate_logs(output_directory, args.days_back, args.verbose)
    if log_count > 0:
        log.info("Copied %s log files." % log_count)
    elif args.verbose > 0:
        log.info("Failed to copy logs")

    if export_postgres_chroma_db(output_directory):
        log.info("Exported manager system database")
    elif args.verbose > 0:
        log.info("Failed to export the manager system database, or none exists.  None exists on target servers.")

    if run_sos:
        if run_command_output_piped(['sosreport', '--batch', '--tmp-dir', output_directory]):
            log.info("Running sosreport")
        else:
            log.info("Failed to run command sosreport")

    change_tree_permissions(output_directory, 0644)

    archive_path = '%s.tar.lzma' % output_directory
    #  Using -C to change to parent of dump dir,
    # then tar.lzma'ing just the output dir
    log.info("Compressing diagnostics into LZMA (archive)")
    run_command_output_piped(
        ['tar', '--lzma', '-cf', archive_path, '-C', default_output_directory, output_fn, '--remove-files'])

    log.info("\nDiagnostic collection is completed.")
    log.info("Size:  %s" % run_command_output_piped(['du', '-h', archive_path]).stdout.read().strip())

    log.info(u"\nThe diagnostic report tar.lzma file can be "
             u"sent to Intel Manager for Lustre Support for analysis.")


if __name__ == "__main__":

    if not os.geteuid() == 0:
        sys.exit("\nOnly root can run this script\n")

    main()
