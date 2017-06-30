# Download and distribute the Lustre kernel packages to yum cache
# Use downloadonly to populate local cache, archive cache then distribute and
# unpack
CACHE_DIR=/var/cache/yum/x86_64/7/lustre
TAR_NAME=lustre-kernel-packages.tar.gz

ssh root@$CLIENT_1 "exec 2>&1; set -xe

sed -i -e '/enabled/a keepcache=1' /etc/yum.repos.d/build.whamcloud.com_job_lustre-b2_10_lastSuccessfulBuild_arch\=x86_64\,build_type\=server\,distro\=el7\,ib_stack\=inkernel_artifact_artifacts_.repo
yum install --downloadonly --disablerepo=* --enablerepo=lustre kernel-*_lustre
cd $CACHE_DIR
tar -cvf ~/$TAR_NAME ./*"

pdsh -l root -R ssh -S -w $(spacelist_to_commalist ${STORAGE_APPLIANCES[@]}) "exec 2>&1; set -xe

cd $CACHE_DIR
ssh $CLIENT_1 'cat ~/$TAR_NAME' | tar xvzf -"
