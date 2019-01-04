#!/usr/bin/env python
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


# chroma-sampling is a commandline command.  Use it to periodically sample
# logs and disk usage for long periods of time.

# Install by copying to the server you want to sample, then doing
# chmod u+x db_disk_growth.py

# To run in Run Forground:
# $ ./db_disk_growth.py -d 60  # sample once per minute

# To Run Background, example
# $ nohup ./db_disk_growth.py -d 60 >/dev/null 2>&1 &

import subprocess
import time
from datetime import datetime
import argparse

LOG_CMD = "du -s /var/log/chroma"
LOG_CMD_STRIPPED = LOG_CMD

DB_CMD = "du -s /var/lib/pgsql"
DB_CMD_STRIPPED = DB_CMD

STATS_TABLES = (
    "chroma_core_sample_10",
    "chroma_core_sample_300",
    "chroma_core_sample_3600",
    "chroma_core_sample_60",
    "chroma_core_sample_86400",
)

STAT_SQL = "select count(id) as rows, pg_relation_size('{0}') as data_length, pg_total_relation_size('{0}') - pg_relation_size('{0}') as index_length from {0};"
STAT_SIZES_SQL_TEMPLATE_CMD = 'psql -U chroma -q chroma -c "%s" ' % STAT_SQL

STATS_SQL_CMD_HEADER = "%s | head -n 3" % STAT_SIZES_SQL_TEMPLATE_CMD
STATS_SQL_CMD_STRIPPED = "%s | tail -n 3 | head -n 1 " % STAT_SIZES_SQL_TEMPLATE_CMD

HEADER_INTERVAL = 10


def _concat_date(cmd):
    """Concatonate date to end of command with some spaces"""

    return 'echo "`%s`        `date -u`"' % cmd


def main():

    parser = argparse.ArgumentParser(description="Sample disk usage for logs " "and data")
    parser.add_argument("--delta_seconds", "-d", type=int, default=300)
    parser.add_argument("--header_rows", "-r", type=int, default=-1)
    args = parser.parse_args()

    time_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    log_sample_filename = "sample_logs_%s" % time_stamp
    db_sample_filename = "sample_db_%s" % time_stamp
    stat_sample_filename_template = "sample_stats_{0}_%s" % time_stamp

    print("Sampling delta:  %s" % args.delta_seconds)
    row = 0
    while True:
        #  print header each args.header_rows num of rows, or only the first row
        header_row = (args.header_rows > 0 and row % args.header_rows == 0) or (args.header_rows < 0 and row == 0)

        cmd = _concat_date(LOG_CMD if header_row else LOG_CMD_STRIPPED)
        cmd = "%s >> %s" % (cmd, log_sample_filename)
        subprocess.Popen(cmd, shell=True)

        cmd = _concat_date(DB_CMD if header_row else DB_CMD_STRIPPED)
        cmd = "%s >> %s" % (cmd, db_sample_filename)
        subprocess.Popen(cmd, shell=True)

        for stat_table in STATS_TABLES:
            cmd = _concat_date(STATS_SQL_CMD_HEADER if header_row else STATS_SQL_CMD_STRIPPED)
            cmd = "%s >> %s" % (cmd, stat_sample_filename_template)
            #  replace {0} with stat_table both in the cmd and the filename
            cmd = cmd.format(stat_table)
            subprocess.Popen(cmd, shell=True)

        row += 1
        time.sleep(args.delta_seconds)


if __name__ == "__main__":
    main()
