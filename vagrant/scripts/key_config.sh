#!/bin/bash

mkdir -m 0700 -p /root/.ssh
cp /vagrant/id_rsa /root/.ssh/.
chmod 0600 /root/.ssh/id_rsa

[ -f /vagrant/id_rsa.pub ] && (awk -v pk="$(cat /vagrant/id_rsa.pub)" 'BEGIN{split(pk,s," ")} $2 == s[2] {m=1;exit}END{if (m==0)print pk}' /root/.ssh/authorized_keys ) >> /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys

cat > /etc/ssh/ssh_config <<__EOF
    Host *
      StrictHostKeyChecking no
__EOF
