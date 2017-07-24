if [ -n "$JENKINS_URL" ]; then
    export JENKINS=true
else
    export JENKINS=false
    export MAKE_TARGET="$1"
fi

[ -r localenv ] && . localenv

spacelist_to_commalist() {
    echo $@ | tr ' ' ','
}

set_distro_vars() {
    distro="$1"

    if [ "$distro" = "el7" ]; then
        if ${upgrade_test}; then
            export TEST_DISTRO_VERSION=${TEST_DISTRO_VERSION:-"7.3"}
            export UPGRADE_DISTRO_VERSION=${UPGRADE_DISTRO_VERSION:-"7.4"}
        else
            export TEST_DISTRO_VERSION=${TEST_DISTRO_VERSION:-"7.4"}
        fi
    else
       if ${upgrade_test}; then
           export TEST_DISTRO_VERSION=${TEST_DISTRO_VERSION:-"6.7"}
           export UPGRADE_DISTRO_VERSION=${UPGRADE_DISTRO_VERSION:-"6.7"}
       else
           export TEST_DISTRO_VERSION=${TEST_DISTRO_VERSION:-"6.7"}
       fi
    fi
}

set_defaults() {
    upgrade_test="$1"

    export CHROMA_DIR=${CHROMA_DIR:-"$PWD/intel-manager-for-lustre/"}

    d=${0%/*}
    if [[ $d != /* ]]; then
        d=${PWD}/$d
    fi
    while [ ! -f $d/include/Makefile.version ]; do
        d=${d%/*}
    done
    export IEEL_VERSION=$(make -s -f $d/include/Makefile.version .ieel_version)
    export SHORT_ARCHIVE_NAME="$(make -s -f $d/include/Makefile.version .short_archive_name)"
    export ARCHIVE_NAME="$SHORT_ARCHIVE_NAME-$IEEL_VERSION.tar.gz"

    export PROVISIONER=${PROVISIONER:-"$HOME/provisionchroma -v -S --provisioner /home/bmurrell/provisioner"}

    if [ "$MEASURE_COVERAGE" != "true" -a "$MEASURE_COVERAGE" != "false" ]; then
        if $JENKINS; then
            {
                echo "Whoa!  We hit TEI-3576."
                echo
                env
                echo
                echo "At test run start, env was:"
                cat /tmp/env-"$JOB_NAME"-"$BUILD_NUMBER"
            } | mail -s "TEI-3576" brian.murrell@intel.com
        fi

        # now set it to a sane value
        MEASURE_COVERAGE="false"
    fi
    rm -f /tmp/env-"$JOB_NAME"-"$BUILD_NUMBER"

    if $JENKINS; then
        JOB_NAME=${JOB_NAME%%/*}
        export JOB_NAME=${JOB_NAME:?"Need to set JOB_NAME"}
        export BUILD_JOB_NAME=${BUILD_JOB_NAME:?"Need to set BUILD_JOB_NAME"}
        export BUILD_JOB_BUILD_NUMBER=${BUILD_JOB_BUILD_NUMBER:?"Need to set BUILD_JOB_BUILD_NUMBER"}
        export JOB_URL=${JOB_URL:?"Need to set JOB_URL"}
        export WORKSPACE=${WORKSPACE:?"Need to set WORKSPACE"}

        if [ "$BUILD_JOB_NAME" = "chroma-reviews-el7" -o \
             "$distro" = "ssi-el7" -o \
             "$distro" = "el7" ] || \
           [[ $slave =~ 7.*\&\&ssi ]]; then
            if [[ $slave = rhel*\&\&ssi ]]; then
                export TEST_DISTRO_NAME=${TEST_DISTRO_NAME:-"rhel"}
            else
                export TEST_DISTRO_NAME=${TEST_DISTRO_NAME:-"el"}
            fi
            export JENKINS_DISTRO="el7"
        else
            export JENKINS_DISTRO="el6.4"
        fi
    else
        export WORKSPACE=workspace
        mkdir -p $WORKSPACE
        export TEST_DISTRO_NAME=${TEST_DISTRO_NAME:-"el"}
        export JENKINS_DISTRO="el7"
    fi
    set_distro_vars "$JENKINS_DISTRO"

    export CLUSTER_CONFIG="cluster_cfg.json"
} # end of set_defaults()
