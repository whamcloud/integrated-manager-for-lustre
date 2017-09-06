[**Table of Contents**](index.md)

# Uninstalling IML

![clustre](md_Graphics/uninstall.jpg)

# **Step 1**: Uninstall the IML Manager

### Stop the manager and httpd 

```
chroma-config stop
```

### Remove the Manager
```
chkconfig --del chroma-supervisor
yum clean all --enablerepo=*
yum remove chroma* fence-agents*
rm -rf /var/lib/chroma/*
rm -rf /usr/share/chroma-manager/
```

### Optionally, remove HTTPD
```
yum remove httpd
For IEEL 3.0, 
yum remove nginx
```

### Reset NTP
```
mv -f /etc/ntp.conf.pre-chroma /etc/ntp.conf
```

### Clean up these RPM included files/dirs
```
rm -rf /usr/lib/python2.6/site-packages/chroma*
```

### Clean up extra yum directories
```
rm -rf /var/lib/yum/repos/x86_64/6/chroma
rm -rf /var/lib/yum/repos/x86_64/6/chroma-manager
rm -rf /var/cache/yum/x86_64/6/chroma
rm -rf /var/cache/yum/x86_64/6/chroma-manager
```

### Optionally, Remove logs
```
rm -rf /var/log/chroma
```

### Optionally, export the database
```
su - postgres 
pg_dump -f chromadb.dump chroma
dropdb chroma
logout
```

### Optionally, remove database server
```
yum remove postgresql*
```

### Optionally stop and remove RabbitMQ
```
service rabbitmq-server stop
yum remove rabbitmq-server
```

### **Note:**  The IML install creates a repo dir based on a tgz distrubtion and a repo file in /etc/yum.repos.d/ however, both repo dir and repo file are completely removed after installation so they should not need to be deleted now.



# **Step 2**: Uninstall the IML Agent

### **Remove Host Action** and **Force Remove Action** will do the following on the manager side:
1. Remove all manager/agent registrations including sessions and queues to prevent any future communication with the host.
1. Remove the hosts cerificate and revoke it's future use.
1. Remove database records for the server and related targets.

### The **Remove Host Action** makes changes to the agent server side. 

In the case of **ForceRemoveHostJob**, the agent side is completely untouched. This is the cause of a few problems and should be used when the communication with the agent is no longer possible. If you do use it, this script can be used to clean up the agent side. You will need to get a shell to the agent machine and issue these commands.

### Note also that although the Remove Host Action will remove IML from the agent, it doesn't do a complete job.

### There are some installed artifacts that are not removed. This script can be used to make sure the server is completely uninstalled.

### Some of the actions below are optional.  If you plan on reinstalling the agent, you may choose not to do the optional items.

### Stop and deregister server
```
service chroma-agent stop
/sbin/chkconfig --del chroma-agent
```

### Remove agent software
```
yum remove chroma-agent chroma-agent-management chroma-diagnostics
```

### Unconfigure NTP
```
mv -f /etc/ntp.conf.pre-chroma /etc/ntp.conf
```

### Erase all cluster information for this server's cluster
### THIS MEANS THAT OTHER NODES IN THE CLUSTER SHOULD BE REMOVED TOO.
```
cibadmin -f -E
```

### Kill pacemaker and corosync
```
killall -9 pacemaker\; killall -9 corosync
```

### Reset firewall setting
### Get the multicast port from the corosync setting, and used in the iptables command
```
grep 'mcastport' /etc/corosync/corosync.conf

rm -f /etc/corosync/corosync.conf

/sbin/iptables -D INPUT -m state --state new -p udp --dport MCAST-PORT -j ACCEPT
REMOVE "-A INPUT -m state --state NEW -m udp -p udp --dport MCAST-PORT -j ACCEPT" from /etc/sysconfig/iptables
REMOVE "--port=MCAST-PORT:udp" from /etc/sysconfig/system-config-firewall
```

## remove pacemaker and corosync
```
yum remove pacemaker-*
yum remove corosync*
rm -f /var/lib/heartbeat/crm/* /var/lib/corosync/*
```

### unconfigure ring1 interface
```
ifconfig $SERVER_RING1 0.0.0.0 down
rm -f /etc/sysconfig/network-scripts/ifcfg-$SERVER_RING1
```

### unconfigure rsyslog
```
Remove lines between # added by chroma-agent\n comments inclusive from /etc/rsyslog.conf See HYD-3090.
```

### unconfigure lnet
```
rm -f /etc/modprobe.d/iml_lnet_module_parameters.conf
```

### umount targets
```
umount -a -tlustre -f
```

### Reset your Linux kernel
### Check the installed kernel, if the kernel has '**lustre**' in the name, then uninstall the kernel.
```
rpm -qR lustre-client-modules | grep 'kernel'
```

### To uninstall the kernel, start by editing: **/etc/grub.conf**
### Change **default = 1** or to point to the stock kernel.

### Save **/etc/grub.conf** and reboot.
**Note:** Editing **/etc/grub.conf** incorrectly can cause boot issues.

### After the system reboots, remove the lustre rpm
```
rpm -q kernel
```

### Example Output:
```
kernel-2.6.32-431.1.2.0.1.el6.x86_64
kernel-2.6.32-431.5.1.el6_lustre.x86_64

This can take a while.
yum remove kernel-2.6.32-431.5.1.el6_lustre.x86_64
```