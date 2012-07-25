#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import time
import sys
from tests.selenium.utils.constants import wait_time
from testconfig import config
from selenium import webdriver
from django.utils.unittest import TestCase

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait


def find_visible_element_by_css_selector(driver, selector):
    """Like find_element_by_css_selector, but restrict search
    to visible elements, and if no visible matches are found
    return None"""
    elements = driver.find_elements_by_css_selector(selector)
    for element in elements:
        try:
            if element.is_displayed():
                return element
        except StaleElementReferenceException:
            pass

    return None


def element_visible(driver, selector):
    elements = driver.find_elements_by_css_selector(selector)
    if not len(elements):
        return None
    elif len(elements) > 1:
        raise RuntimeError("Selector %s matches multiple elements!" % selector)
    else:
        element = elements[0]

    try:
        if element.is_displayed():
            return element
        else:
            return None
    except StaleElementReferenceException:
        return None


def wait_for_element(driver, selector, timeout):
    for i in xrange(timeout):
        element = element_visible(driver, selector)
        if element:
            return element

        time.sleep(1)
    raise RuntimeError("Timed out after %s seconds waiting for %s" % (timeout, selector))


def wait_for_any_element(driver, selectors, timeout):
    for i in xrange(timeout):
        if isinstance(selectors, str) or isinstance(selectors, unicode):
            element = find_visible_element_by_css_selector(driver, selectors)
            if element:
                return element
        else:
            for s in selectors:
                element = element_visible(driver, s)
                if element:
                    return element

        time.sleep(1)
    raise RuntimeError("Timeout after %s seconds waiting for any of %s" % (timeout, selectors))


def wait_for_transition(driver, timeout):
    """Wait for a job to complete.  NB the busy icon must be visible initially
    (call quiesce after state change operations to ensure that if the busy icon
    is going to appear, it will have appeared)"""

    for timer in xrange(timeout):
        if element_visible(driver, "img#notification_icon_jobs"):
            time.sleep(1)
        else:
            # We have to quiesce here because the icon is hidden on command completion
            # but updates to changed objects are run asynchronously.
            quiesce_api(driver, timeout)
            return

    raise RuntimeError('Timeout after %s seconds waiting for transition to complete' % timeout)


def enter_text_for_element(driver, selector_or_element, text_value):
    if isinstance(selector_or_element, str) or isinstance(selector_or_element, unicode):
        element = driver.find_element_by_css_selector(selector_or_element)
    else:
        element = selector_or_element
    element.clear()
    element.send_keys(text_value)
    WebDriverWait(driver, 10).until(lambda driver: element.get_attribute('value') == text_value)


def click_element_and_wait(driver, xpath_selector, timeout):
    element = driver.find_element_by_xpath(xpath_selector)
    element.click()
    wait_for_transition(driver, timeout)


def select_element_option(driver, selector, index):
    element = driver.find_element_by_css_selector(selector)
    element_options = element.find_elements_by_tag_name('option')
    element_options[index].click()


def get_selected_option_text(driver, dropdown_element_selector):
    selectbox_element = Select(driver.find_element_by_css_selector(dropdown_element_selector))
    return selectbox_element.first_selected_option.text


def quiesce_api(driver, timeout):
    for i in xrange(timeout):
        busy = driver.execute_script('return ($.active != 0);')
        if not busy:
            return
        else:
            time.sleep(1)
    raise RuntimeError('Timeout')


def login(driver, username, password):
    """Login with given username and password"""
    from tests.selenium.views.login import Login
    wait_for_any_element(driver, ['#login_dialog', '#user_info #anonymous #login'], 10)
    login_view = Login(driver)
    if not element_visible(driver, '#login_dialog'):
        login_view.open_login_dialog()
    login_view.login_user(username, password)


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

    def setUp(self):
        if config['headless']:
            from pyvirtualdisplay import Display
            display = Display(visible = 0, size = (1280, 1024))
            display.start()

        if not self.driver:
            self.driver = getattr(webdriver, config['chroma_managers']['browser'])()

        self.wait_time = wait_time['standard']
        self.long_wait_time = wait_time['long']
        if not config['chroma_managers']['server_http_url']:
            raise RuntimeError("Please set server_http_url in config file")
        self.driver.get(config['chroma_managers']['server_http_url'])

        superuser_present = False
        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                login(self.driver, user['username'], user['password'])
                superuser_present = True

        if not superuser_present:
            raise RuntimeError("No superuser in config file")

        wait_for_element(self.driver, '#user_info #authenticated', 10)
        wait_for_element(self.driver, '#dashboard_menu', 10)

        from tests.selenium.utils.navigation import Navigation
        self.navigation = Navigation(self.driver)

        self.clear_all()

    def tearDown(self):
        # On successful tests, clean up (attribute errors cleaning up to the test
        # that got the system into a state rather than to the next test that runs)
        # On failing tests, do not clean up -- leave the system in a state for
        # human investigation.  If another test runs, it will clean up then.
        if sys.exc_info() == (None, None, None):
            self.log.info("Cleaning up after success")
            # Return to base URI to get away from any dialogs that
            # might block navigation during clear_all
            self.navigation.reset()

            self.clear_all()
            self.driver.close()

    def clear_all(self):
        from tests.selenium.views.filesystem import Filesystem
        from tests.selenium.views.mgt import Mgt
        from tests.selenium.views.servers import Servers

        self.log.info("Clearing all objects")
        self.navigation.go('Configure', 'Filesystems')
        Filesystem(self.driver).remove_all()
        self.navigation.go('Configure', 'MGTs')
        Mgt(self.driver).remove_all()
        self.navigation.go('Configure', 'Servers')
        Servers(self.driver).remove_all()

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
