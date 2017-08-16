#!/bin/bash

collect_reports() {

    echo "Collecting reports..."

    scp root@$TEST_RUNNER:~/test_report*.xml "$PWD/test_reports/"

    if $MEASURE_COVERAGE; then
        ssh root@$CHROMA_MANAGER chroma-config stop

        pdsh -l root -R ssh -S -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} ${WORKERS[@]}) "set -x
# https://github.com/pypa/virtualenv/issues/355
python_version=\$(python -c 'import platform; print \".\".join(platform.python_version_tuple()[0:2])')
rm -f /usr/lib/python\$python_version/site-packages/sitecustomize.py*
cd /var/tmp/
coverage combine
# when putting the pdcp below back, might need to install pdsh first
#      yum -y install pdsh" | dshbak -c
        if [ ${PIPESTATUS[0]} != 0 ]; then
            exit 1
        fi

        # TODO: should use something like this for better efficiency:
        # rpdcp -l root -R ssh -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} ${WORKERS[@]}) /var/tmp/.coverage $PWD
        for SERVER in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} ${WORKERS[@]}; do
            scp root@$SERVER:/var/tmp/.coverage .coverage.\$SERVER
        done

        ssh root@$CHROMA_MANAGER chroma-config start
    fi
}
