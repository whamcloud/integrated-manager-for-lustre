#!/bin/bash

cd /integrated-manager-for-lustre
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce
sudo systemctl enable --now docker
sudo curl -L "https://github.com/docker/compose/releases/download/1.26.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/bin/docker-compose
sudo chmod +x /usr/bin/docker-compose

pushd docker
sudo make save
popd
sudo DOCKER_BUILDKIT=1  docker run -e SPEC="iml-docker.spec" -e SRPM_TASK="iml-docker-srpm" -e LOCAL_ONLY="True" -v $(pwd):/build:rw imlteam/copr

yum install -y /integrated-manager-for-lustre/_topdir/RPMS/x86_64/iml-docker*.rpm
docker swarm init --advertise-addr=127.0.0.1 --listen-addr=127.0.0.1

# Password
echo "lustre" > /etc/iml-docker/setup/password
docker secret create iml_pw /etc/iml-docker/setup/password

cat <<EOF > /etc/iml-docker/docker-compose.overrides.yml
version: "3.7"

services:
  job-scheduler:
    extra_hosts:
      - "adm.local:10.73.10.10"
      - "mds1.local:10.73.10.11"
      - "mds2.local:10.73.10.12"
      - "oss1.local:10.73.10.21"
      - "oss2.local:10.73.10.22"
      - "client1.local:10.73.10.31"
    environment:
      - "NTP_SERVER_HOSTNAME=adm.local"
  iml-warp-drive:
    environment:
      - RUST_LOG=debug
  iml-action-runner:
    environment:
      - RUST_LOG=debug
  iml-api:
    environment:
      - RUST_LOG=debug
  iml-ostpool:
    environment:
      - RUST_LOG=debug
  iml-stats:
    environment:
      - RUST_LOG=debug
  iml-agent-comms:
    environment:
      - RUST_LOG=debug
  device:
    environment:
      - RUST_LOG=debug
  network:
    environment:
      - RUST_LOG=debug
EOF

# Enable but do not start iml-docker
systemctl enable iml-docker
