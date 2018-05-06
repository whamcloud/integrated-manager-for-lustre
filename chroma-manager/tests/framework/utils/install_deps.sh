# Copy the repo to the test node (don't want to have to clone every test run - impacts Gerrit)
tar -czf - . | ssh chromatest@$CHROMA_MANAGER "set -ex
mkdir -p chroma_test_env
tar -C chroma_test_env -xizf -"

ssh root@$CHROMA_MANAGER "set -ex
yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/joegrund/manager-for-lustre/repo/epel-7/joegrund-manager-for-lustre-epel-7.repo
yum -y install nodejs npm nginx libuv iml-gui iml-srcmap-reverse iml-online-help"
