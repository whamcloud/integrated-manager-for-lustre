# EXAScaler Management Framework

Simple, but powerful, management tools that provide a unified, consistent view of Lustre storage systems and simplify the installation, configuration, monitoring, and overall management of Lustre.

## How to test EMF (vagrant)
1. Install vagrant and virtualbox
see https://learn.hashicorp.com/tutorials/vagrant/getting-started-install?in=vagrant/getting-started

2. Download an EXAScaler box from http://10.52.16.26/artifacts/isos/exascaler/5.2.2/master/images/ and add it in vagrant (must be on VPN).
```sh
wget http://10.52.16.26/artifacts/isos/exascaler/5.2.2/master/images/es-5.2.2-server-centos-r4-x86_64.box && \
vagrant box add exascaler/5.2.2_r4 es-5.2.2-server-centos-r4-x86_64.box
```

3. Create the default hostonlyif needed by the cluster
```sh
VBoxManage hostonlyif create
```

4. In the root directory, download emf rpms and put them in emf-repo-rpm/
```sh
# Download from https://github.com/whamcloud/exascaler-management-framework/releases/download/untagged-24ffe7bfe19fb4baa13f/emf_repo_rpm.zip
unzip -o emf_repo_rpm.zip -d emf-repo-rpm
```

5. Update your ssh config file
```sh
./es_vagrant/update_ssh_config.sh
```

6. Run the following commands in es-vagrant directory
```sh
make destroy 
EXASCALER=5.2.2_r2 vagrant up 
vagrant provision --provision-with=reset-machine-id,es-install
vagrant provision --provision-with=ha-setup,start-lustre 
scp -r ../emf-repo-rpm/ node1:~/ 
vagrant provision --provision-with=emf-remove-old-bits,emf-install-repo,emf-deploy
```

7. ssh on node1 and verify that it worked
```sh
ssh node1
emf command show 1
```

ℹ From there you can create a snapshot to speed-up the development
⚠  Lustre targets use shareable disks and so are not snapshotted
```sh
ssh node1 "esctl cluster --action stop"
vagrant snapshot push # Must be run in es-vagrant
# To restore
# vagrant snapshot pop --no-delete # Must be run in es-vagrant
# ssh node1 "esctl cluster --action start"
```

## Modify SQLx queries

A local db is required only when making changes to the SQLx queries in this repo.
In order to interact with a running database:

1. Install postgresql and create a new user called emf
```sh
# See https://www.postgresql.org/download/ to install postgresql
# Also install the contrib package (e.g 'yum install postgresql13-contrib')
useradd emf # Create new POSIX user emf
sudo -u postgres createuser emf # Create postgres emf user
```
2. Create a new database called emf belonging to emf
```sh
sudo -u postgres make nuke_db # Delete and recreate the emf DB
```

3. Add a `.env` file in this directory with a `DATABASE_URL` environment variable.
For example, to connect to a local emf db running on localhost the `.env` file would look like:

```sh
echo "DATABASE_URL=postgres://emf@localhost:5432/emf
# If it can't connect, try with DATABASE_URL=postgres://localhost:5432?dbname=emf&password=emf&user=emf" > .env
```

Once you have a db configured migrations can be run with:

```sh
. .env && make migrate_db
```

⚠  If the make migrate_db fail you may have to delete and create again the emf database.
Copy/paste the following lines and re-run make migrate_db.
```sh
sudo -u postgres make nuke_db
```

Once a change has been made to a query, run the following in this directory:

```sh
cargo sqlx prepare --merged -- --tests
```

You can check if the generated queries are up to date with:

```sh
cargo sqlx prepare --merged --check -- --tests
```

You may need to install the sqlx-cli as well:

```sh
cargo install sqlx-cli --no-default-features --features postgres
```


Precommit checks are run by [rusty-hook](https://github.com/swellaby/rusty-hook). To setup do the following:

```sh
cargo install --git https://github.com/swellaby/rusty-hook.git
rusty-hook init # In this directory
```
