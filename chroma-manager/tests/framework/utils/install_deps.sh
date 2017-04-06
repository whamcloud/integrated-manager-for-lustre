# Copy the repo to the test node (don't want to have to clone every test run - impacts Gerrit)
# We exclude chroma-externals and copy just what we need to reduce the io load on our builders.
TEST_DEPS="${0%/*}/test_dependencies"

(
    tar -czf - --exclude="$REL_CHROMA_DIR/chroma-externals*" .
    tar -czf - $(sed -e "s|^|$REL_CHROMA_DIR/chroma-externals/|" < $TEST_DEPS)
    tar -czf - $REL_CHROMA_DIR/chroma-externals/*.zip $REL_CHROMA_DIR/chroma-externals/*.tar.*
) | ssh chromatest@$CHROMA_MANAGER "mkdir -p chroma_test_env
tar -C chroma_test_env -xizf -"

ssh root@$CHROMA_MANAGER "set -ex
yum -y install nodejs npm nginx libuv"
