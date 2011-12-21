#!/bin/bash

export WORKER_NAMES="serialize periodic ssh jobs parselog"
export PIDFILE="celery_%n.pid"
export LOGFILE="celery_%n.log"
export MANAGE_PY="./manage.py"

rm -f celery_*.pid celery_*.log

echo "Starting..."

python ${MANAGE_PY} celeryd_multi start ${WORKER_NAMES} -Q:serialize serialize -Q:periodic periodic -Q:ssh ssh -Q:jobs jobs -Q:parselog parselog -c:parselog 1 -B:periodic -c:periodic 1 -c:serialize 1 -c:ssh 1 -c:jobs 8 --pidfile=$PIDFILE --logfile=$LOGFILE

configure/bin/storage_daemon 2>storage_daemon_err.log > storage_daemon_out.log &
echo $! > storage_daemon.pid

python manage.py runserver_plus --noreload 0.0.0.0:8000 2> runserver_err.log > runserver_out.log &
echo $! > runserver.pid

log4tail *.log

echo "Stopping celery workers..."
python ${MANAGE_PY} celeryd_multi stop ${WORKER_NAMES} --pidfile=$PIDFILE --logfile=$LOGFILE
echo "Killing celery workers..."
python ${MANAGE_PY} celeryd_multi kill ${WORKER_NAMES} --pidfile=$PIDFILE --logfile=$LOGFILE

echo "Killing storage_daemon..."
kill `cat storage_daemon.pid`
sleep 2
kill -9 `cat storage_daemon.pid`

echo "Killing run_server..."
kill `cat runserver.pid`
kill -9 `cat runserver.pid`

echo "Any stragglers?"

ps aux | grep celeryd
