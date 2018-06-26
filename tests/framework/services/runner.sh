#!/bin/bash -ex

yum install -y epel-release
yum install -y git python-virtualenv python-setuptools python-devel gcc make graphviz-devel postgresql-server postgresql-devel rabbitmq-server telnet python-ethtool erlang-inets patch gcc-c++ systemd-devel python-pip curl libcurl-devel nss
systemctl enable rabbitmq-server

export PATH=$PATH:/usr/lib/rabbitmq/bin/
rabbitmq-plugins enable rabbitmq_management
systemctl start rabbitmq-server
journalctl -u rabbitmq-server --no-pager


# Testing rabbitmq and wait to be up and running
COUNTER=0
MAX_TRIALS=15
rabbitmqctl status
while [[ $? -ne 0 && $COUNTER -ne $MAX_TRIALS ]];
    do
    sleep 2
    let COUNTER=COUNTER+1
    rabbitmqctl status
done;
echo "counter: $COUNTER, trials: $MAX_TRIALS"
[[ $COUNTER -eq $MAX_TRIALS ]] && { echo 'RabbitMQ cannot be started!'; exit 1; }


# Testing rabbitmq internal messaging
curl http://localhost:15672/cli/rabbitmqadmin > $HOME/rabbitmqadmin
chmod u+x $HOME/rabbitmqadmin
$HOME/rabbitmqadmin declare queue name=test-queue durable=false
$HOME/rabbitmqadmin publish exchange=amq.default routing_key=test-queue payload="test_message"


COUNTER=0
grep_msg="$HOME/rabbitmqadmin get queue=test-queue requeue=false | grep test_message"
while [[ $(eval $grep_msg) == "" && $COUNTER -ne $MAX_TRIALS ]];
    do
    sleep 2
    let COUNTER=COUNTER+1
done;
echo "counter: $COUNTER, trials: $MAX_TRIALS"
[[ $COUNTER -eq $MAX_TRIALS ]] && { echo 'RabbitMQ cannot receive messages!'; exit 1; }


# Configure postgres
systemctl enable postgresql
postgresql-setup initdb
systemctl start postgresql
# TODO: sleeping is racy.  should check for up-ness, not just assume it
#       will happen within 5 seconds
sleep 5  # Unfortunately postgresql start seems to return before its truly up and ready for business
su postgres -c 'createuser -R -S -d chroma'
su postgres -c 'createdb -O chroma chroma'
sed -i -e '/local[[:space:]]\+all/i\
local   all         chroma                            trust' /var/lib/pgsql/data/pg_hba.conf
systemctl restart postgresql


yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre-devel/repo/epel-7/managerforlustre-manager-for-lustre-devel-epel-7.repo
yum -y install nodejs npm nginx libuv iml-gui iml-srcmap-reverse iml-online-help iml-view-server iml-old-gui iml-realtime

cd /integrated-manager-for-lustre
cp iml-corosync.service iml-gunicorn.service iml-http-agent.service iml-job-scheduler.service /lib/systemd/system
cp iml-lustre-audit.service iml-manager.target iml-plugin-runner.service iml-power-control.service /lib/systemd/system
cp iml-settings-populator.service iml-stats.service iml-syslog.service /lib/systemd/system
pip install -r requirements.txt

cd /integrated-manager-for-lustre
PYTHONPATH=. python ./scripts/production_nginx.py chroma-manager.conf.template > /etc/nginx/conf.d/chroma-manager.conf

cp -r /integrated-manager-for-lustre /usr/share/chroma-manager
mkdir /var/log/chroma
cd /usr/share/chroma-manager

python ./manage.py dev_setup --no-bundles
PYTHONPATH=. nosetests tests/services/ --stop