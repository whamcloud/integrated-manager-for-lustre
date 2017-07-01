# Download and distribute the Lustre kernel packages to yum cache
# Use downloadonly to populate local cache, archive cache then distribute and
# unpack
CACHE_DIR=/var/cache/yum/x86_64/7/lustre
TAR_NAME=lustre-kernel-packages.tar.gz

ssh root@$CLIENT_1 "exec 2>&1; set -xe

# for improved reliability, extend retries and timeout.
# set keepcache to populate cache with downloaded packages
sed -i -e '/enabled/a keepcache=1' -e '/enabled/a retries=20' -e '/enabled/a timeout=60' /etc/yum.repos.d/build.whamcloud.com_lustre-b2_10_last_successful_.repo

yum install --downloadonly --skip-broken kernel-*_lustre

cd $CACHE_DIR
tar -cvf ~/$TAR_NAME ./*"

pdsh -l root -R ssh -S -w $(spacelist_to_commalist ${STORAGE_APPLIANCES[@]}) "exec 2>&1; set -xe

cd $CACHE_DIR
ssh $CLIENT_1 'cat ~/$TAR_NAME' | tar xvzf -"
