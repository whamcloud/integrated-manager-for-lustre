#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import time
import sys

from django.utils.unittest import TestCase
from selenium import webdriver
from testconfig import config

from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.element import (
    find_visible_element_by_css_selector, wait_for_element_by_css_selector
)


def quiesce_api(driver, timeout):
    for i in xrange(timeout):
        busy = driver.execute_script('return ($.active != 0);')
        if not busy:
            return
        else:
            time.sleep(1)
    raise RuntimeError('Timeout')


def wait_for_transition(driver, timeout):
    """Wait for a job to complete.  NB the busy icon must be visible initially
    (call quiesce after state change operations to ensure that if the busy icon
    is going to appear, it will have appeared)"""

    for timer in xrange(timeout):
        if find_visible_element_by_css_selector(driver, "img#notification_icon_jobs"):
            time.sleep(1)
        else:
            # We have to quiesce here because the icon is hidden on command completion
            # but updates to changed objects are run asynchronously.
            quiesce_api(driver, timeout)
            return

    raise RuntimeError('Timeout after %s seconds waiting for transition to complete' % timeout)


log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)


class SeleniumBaseTestCase(TestCase):
    """This is the base class for the test classes.
    The setUp() method is called during the
    initialization process. The tearDown() method is called
    irrespective of the status of the application.
    """
    def __init__(self, *args, **kwargs):
        super(SeleniumBaseTestCase, self).__init__(*args, **kwargs)
        self.log = log

        self.driver = None
        self.standard_wait = wait_time['standard']
        self.medium_wait = wait_time['medium']
        self.long_wait = wait_time['long']

    def setUp(self):
        if not config['chroma_managers']['server_http_url']:
            raise RuntimeError("Please set server_http_url in config file")

        if config['headless']:
            from pyvirtualdisplay import Display
            display = Display(visible = 0, size = (1280, 1024))
            display.start()

        if not self.driver:
            browser = config['chroma_managers']['browser']
            if browser == 'Chrome':
                options = webdriver.ChromeOptions()
                options.add_argument('no-proxy-server')
                self.driver = getattr(webdriver, browser)(chrome_options=options)
            elif browser == 'Firefox':
                self.driver = webdriver.Firefox()

        self.driver.get(config['chroma_managers']['server_http_url'])

        from tests.selenium.utils.navigation import Navigation
        self.navigation = Navigation(self.driver)

        superuser_present = False
        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                self.navigation.login(user['username'], user['password'])
                superuser_present = True
        if not superuser_present:
            raise RuntimeError("No superuser in config file")

        wait_for_element_by_css_selector(self.driver, '#user_info #authenticated', 10)
        wait_for_element_by_css_selector(self.driver, '#dashboard_menu', 10)

        self.clear_all()

    def tearDown(self):
        # It can be handy not to clean up after a failed test when a developer
        # is actively working on a test or troubleshooting a test failure and
        # to leave the browser window open. To provide for this, there is an
        # option in the config, clean_up_on_failure, that controls clean up on
        # failed tests. Cleanup will always occur for successful tests.
        # Beware that the un-cleaned-up tests will leave resources and processes
        # on your system that will not automatically be cleaned up.
        test_failed = False if sys.exc_info() == (None, None, None) else True
        if config.get('clean_up_on_failure'):
            self.log.info("Cleaning up after %s" % 'failure' if test_failed else 'success')
            self.driver.quit()
        elif not test_failed:
            self.log.info("Cleaning up after success")
            self.driver.close()

    def clear_all(self):
        from tests.selenium.views.filesystem import Filesystem
        from tests.selenium.views.mgt import Mgt
        from tests.selenium.views.servers import Servers
        from tests.selenium.views.users import Users

        self.log.info("Clearing all objects")
        self.navigation.go('Configure', 'Filesystems')
        Filesystem(self.driver).remove_all()
        self.navigation.go('Configure', 'MGTs')
        Mgt(self.driver).remove_all()
        self.navigation.go('Configure', 'Servers')
        Servers(self.driver).remove_all()

        superuser_username = None
        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                superuser_username = user['username']
        if not superuser_username:
            raise RuntimeError("Test config does not define a superuser")
        else:
            self.navigation.go('Configure', 'Users')
            Users(self.driver).delete_all_except(superuser_username)

    def volume_and_server(self, index):
        volume = config['volumes'][index]

        # Pick an arbitrary server as the primary
        try:
            server = volume['servers'].keys()[0]
        except (IndexError, KeyError):
            raise RuntimeError("No servers for volume %s/%s" % (index, volume['id']))
        else:
            return volume['label'], server

    def create_filesystem_with_server_and_mgt(self, host_list,
                                              mgt_host_name, mgt_device_node,
                                              filesystem_name,
                                              mdt_host_name, mdt_device_node,
                                              ost_host_name, ost_device_node, conf_params):
        from tests.selenium.views.volumes import Volumes
        from tests.selenium.views.mgt import Mgt
        from tests.selenium.views.servers import Servers
        from tests.selenium.views.create_filesystem import CreateFilesystem
        from tests.selenium.views.conf_param_dialog import ConfParamDialog

        self.log.info("Creating filesystem: %s MGT:%s/%s, MDT %s/%s, OST %s/%s" % (
            filesystem_name,
            mgt_host_name, mgt_device_node,
            mdt_host_name, mdt_device_node,
            ost_host_name, ost_device_node))

        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(host_list)

        self.navigation.go('Configure', 'Volumes')
        volume_page = Volumes(self.driver)
        for primary_server, volume_name in [(mgt_host_name, mgt_device_node), (mdt_host_name, mdt_device_node), (ost_host_name, ost_device_node)]:
            volume_page.set_primary_server(volume_name, primary_server)

        self.navigation.go('Configure', 'MGTs')
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(mgt_host_name, mgt_device_node)

        self.navigation.go('Configure', 'Create_new_filesystem')
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(filesystem_name)
        create_filesystem_page.open_conf_params()
        ConfParamDialog(self.driver).enter_conf_params(conf_params)
        create_filesystem_page.close_conf_params()
        create_filesystem_page.select_mgt(mgt_host_name)
        create_filesystem_page.select_mdt_volume(mdt_host_name, mdt_device_node)
        create_filesystem_page.select_ost_volume(ost_host_name, ost_device_node)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        wait_for_transition(self.driver, self.long_wait)

    def create_filesystem_simple(self, host_list, filesystem_name, conf_params = None):
        """Pick some arbitrary hosts and volumes to create a filesystem"""
        if conf_params is None:
            conf_params = {}

        self.mgt_volume_name, self.mgt_server_address = self.volume_and_server(0)
        self.mdt_volume_name, self.mdt_server_address = self.volume_and_server(1)
        self.ost_volume_name, self.ost_server_address = self.volume_and_server(2)

        self.create_filesystem_with_server_and_mgt(
            host_list,
            self.mgt_server_address, self.mgt_volume_name,
            filesystem_name,
            self.mdt_server_address, self.mdt_volume_name,
            self.ost_server_address, self.ost_volume_name,
            conf_params)
