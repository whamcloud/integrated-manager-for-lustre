#!/bin/sh

# Start the jobber daemon
/usr/libexec/jobberrunner -u /var/jobber/1000/cmd.sock /home/jobberuser/.jobber &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start jobber daemon: $status"
  exit $status
fi

# Start the iml-jobber http server
/usr/local/bin/iml-jobber &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start iml-jobber http server: $status"
  exit $status
fi

# Naive check runs checks once a minute to see if either of the processes exited.
# This illustrates part of the heavy lifting you need to do if you want to run
# more than one service in a container. The container exits with an error
# if it detects that either of the processes has exited.
# Otherwise it loops forever, waking up every 60 seconds

while sleep 60; do
  # ps aux |grep jobberd |grep -q -v grep
  # PROCESS_1_STATUS=$?
  ps aux |grep iml-jobber |grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the jobber processes exited."
    exit 1
  fi
done