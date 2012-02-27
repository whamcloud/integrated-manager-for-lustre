"""Unit Testing code for the chroma UI
"""

# Import system modules
from django.utils.unittest import TestCase

# Import third-party modules
from selenium import webdriver

from utils.constants import Constants
import test_parameters

import time
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException

from utils.navigation import Navigation


def element_visible(driver, selector):
    try:
        element = driver.find_element_by_css_selector(selector)
        try:
            if element.is_displayed():
                return True
        except StaleElementReferenceException:
            return False
    except NoSuchElementException:
        return False


def wait_for_element(driver, selector, timeout):
    for i in xrange(timeout):
        if element_visible(driver, selector):
            return

        time.sleep(1)
    raise RuntimeError('Timeout')


def wait_for_any_element(driver, selectors, timeout):
    for i in xrange(timeout):
        for s in selectors:
            if element_visible(driver, s):
                return

        time.sleep(1)
    raise RuntimeError('Timeout')


def wait_for_datatable(driver, selector, timeout = 10):
    # A loaded datatable always has at least one tr, either
    # a real record or a "no data found" row
    wait_for_element(driver, selector + " tbody tr", timeout)


def quiesce_api(driver, timeout):
    for i in xrange(timeout):
        busy = driver.execute_script('Api.busy();')
        if not busy:
            return
    raise RuntimeError('Timeout')


class SeleniumBaseTestCase(TestCase):
    """This is the base class for the test classes.
    The setUp() method is called during the
    initialization process. The tearDown() method is called
    irrespective of the status of the application.
    """
    driver = None

    def setUp(self):
        from views.login import Login

        if test_parameters.HEADLESS:
            from pyvirtualdisplay import Display
            display = Display(visible = 0, size = (1280, 1024))
            display.start()

        if not self.driver:
            self.driver = getattr(webdriver, test_parameters.BROWSER)()

        constants = Constants()
        self.wait_time = constants.get_wait_time('standard')
        self.long_wait_time = constants.get_wait_time('long')
        if not test_parameters.CHROMA_URL:
            raise RuntimeError("Please set test_parameters.CHROMA_URL")
        self.driver.get(test_parameters.CHROMA_URL)

        wait_for_any_element(self.driver, ['#login_dialog', '#user_info #anonymous #login'], 10)
        login_view = Login(self.driver)
        if not element_visible(self.driver, '#login_dialog'):
            login_view.open_login_dialog()
        login_view.login_superuser()
        wait_for_element(self.driver, '#user_info #authenticated', 10)
        wait_for_element(self.driver, '#dashboard_menu', 10)
        self.driver.execute_script('Api.testMode(true);')
        self.navigation = Navigation(self.driver)

    def tearDown(self):
        self.driver.close()
