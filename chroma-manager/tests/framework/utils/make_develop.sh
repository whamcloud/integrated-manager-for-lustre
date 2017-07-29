ssh chromatest@$CHROMA_MANAGER "set -ex

virtualenv chroma_test_env
source chroma_test_env/bin/activate
cd chroma_test_env/$REL_CHROMA_DIR/chroma-manager
make requirements.txt
echo \"jenkins_fold:start:pip install requirements.txt\"
if ${INSTALL_PYCURL:-false}; then
    # install pycurl (as required by fencing.py) on el7
    if [[ \$(rpm --eval %rhel) == 7 ]]; then
        export PYCURL_SSL_LIBRARY=nss
        pip install --upgrade pip
        pip install --compile pycurl==7.43.0
    fi
fi
make install_requirements
echo \"jenkins_fold:end:pip install requirements.txt\"

if $MEASURE_COVERAGE; then
  cat <<EOC > /home/chromatest/chroma_test_env/$REL_CHROMA_DIR/chroma-manager/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /home/chromatest/chroma_test_env/$REL_CHROMA_DIR
EOC
  # https://github.com/pypa/virtualenv/issues/355
  python_version=\$(python -c 'import platform; print \".\".join(platform.python_version_tuple()[0:2])')
  cat <<EOC  > /home/chromatest/chroma_test_env/lib/python\$python_version/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/home/chromatest/chroma_test_env/$REL_CHROMA_DIR/chroma-manager/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOC
fi

# Enable DEBUG logging
cat <<\"EOF1\" > local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

export NPM_CONFIG_PYTHON=/usr/bin/python
make develop"
