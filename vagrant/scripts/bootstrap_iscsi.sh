#!/bin/bash

ISCI_IP=$1
ISCI_IP2=$2
IDX=1

yum -y install targetcli lsscsi
targetcli /backstores/block create mgt1 /dev/sdb
targetcli /backstores/block create mdt1 /dev/sdc
targetcli /backstores/block create mdt2 /dev/sdd
targetcli /backstores/block create mdt3 /dev/sde
targetcli /iscsi set global auto_add_default_portal=false
targetcli /iscsi create iqn.2015-01.com.whamcloud.lu:mds
targetcli /iscsi create iqn.2015-01.com.whamcloud.lu:oss
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/luns/ create /backstores/block/mgt1
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/luns/ create /backstores/block/mdt1
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/luns/ create /backstores/block/mdt2
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/luns/ create /backstores/block/mdt3


for x in {f..y}
do
    targetcli /backstores/block create ost${IDX} /dev/sd${x}
    targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:oss/tpg1/luns/ create /backstores/block/ost${IDX}
    ((IDX++))
done

targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/portals/ create ${ISCI_IP}
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:oss/tpg1/portals/ create ${ISCI_IP}
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/portals/ create ${ISCI_IP2}
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:oss/tpg1/portals/ create ${ISCI_IP2}
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/acls create iqn.2015-01.com.whamcloud:mds1
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:mds/tpg1/acls create iqn.2015-01.com.whamcloud:mds2
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:oss/tpg1/acls create iqn.2015-01.com.whamcloud:oss1
targetcli /iscsi/iqn.2015-01.com.whamcloud.lu:oss/tpg1/acls create iqn.2015-01.com.whamcloud:oss2
targetcli saveconfig
systemctl enable target
