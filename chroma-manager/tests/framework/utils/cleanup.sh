cleanup() {
    set -x
    set +e
    if $got_aborted; then
        tmpfile=/tmp/abort.$$.debug
        exec 2>$tmpfile
        env >&2
    fi
    python $CHROMA_DIR/chroma-manager/tests/integration/utils/chroma_log_collector.py $WORKSPACE/test_logs $CLUSTER_CONFIG | tee $WORKSPACE/log_collector_out 2>&1 || true
    # look for known failures in the logs
    if grep "LDISKFS-fs (.*): group descriptors corrupted" $WORKSPACE/test_logs/*-messages.log; then
        echo "bug: TEI-39" test_output
    fi
    if egrep "^ssh: Could not resolve hostname lotus-[0-9][0-9]*vm1*4\.iml\.intel\.com: Name or service not known" $WORKSPACE/log_collector_out; then
        echo "bug: TEI-1327"
    fi
    rm -f $WORKSPACE/log_collector_out
    if grep "AssertionError: 300 not less than 300 : Timed out waiting for host to come back online" $WORKSPACE/test_logs/*-chroma_test.log; then
        echo "bug: HYD-2889"
    fi
    if grep "Could not match packages: Cannot retrieve repository metadata (repomd.xml) for repository: lustre-client. Please verify its path and try again" $WORKSPACE/test_logs/*-chroma_test.log; then
        echo "bug: HYD-2948"
    fi

    if [ -f $CHROMA_DIR/chroma-manager/tests/framework/utils/provisioner_interface/release_cluster ]; then
        $CHROMA_DIR/chroma-manager/tests/framework/utils/provisioner_interface/release_cluster || true
    else
        {
        echo "*****************************************************************"
        echo "$CHROMA_DIR/chroma-manager/tests/framework/utils/provisioner_interface/release_cluster could not be found"
        if $got_aborted; then
            echo "this job was aborted!!"
        fi
        pwd
        ls -l $CHROMA_DIR
        echo "*****************************************************************"
        } >&2
    fi

    echo "exit trap done" >&2
    if [ -n "$tmpfile" -a -e "$tmpfile" ]; then
        cat $tmpfile | mail -s "job aborted" brian.murrell@intel.com
        #rm $tmpfile
    fi
}
