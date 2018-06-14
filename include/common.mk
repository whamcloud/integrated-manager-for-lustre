travis_mock_build_test:
	TRAVIS=true TRAVIS_EVENT_TYPE=pull_request \
	    TRAVIS_PULL_REQUEST_BRANCH=$${TRAVIS_PULL_REQUEST_BRANCH:-master} \
            include/travis/run_in_centos7_docker.sh \
	        include/travis/mock_build_test.sh

clean:
	if [ -n "$(CLEAN)" ]; then \
	    rm -rf $(CLEAN);       \
	fi

distclean: clean
	if [ -n "$(DISTCLEAN)" ]; then \
	    rm -rf $(DISTCLEAN);       \
	fi
