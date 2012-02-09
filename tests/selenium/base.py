"""Unit Testing code for the chroma UI
"""

# Import system modules
from django.utils.unittest import TestCase

# Import third-party modules
from selenium import webdriver

from utils.constants import Constants
import test_parameters

from views.login import Login

import time
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException


def wait_for_css_selector_visible(driver, selector, timeout):
    for i in xrange(timeout):
        try:
            element = driver.find_element_by_css_selector(selector)
            try:
                if element.is_displayed():
                    return
            except StaleElementReferenceException:
                pass
        except NoSuchElementException:
            pass
        time.sleep(1)
    raise RuntimeError('Timeout')


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

        wait_for_css_selector_visible(self.driver, '#login_dialog', 10)
        Login(self.driver).login_superuser()
        wait_for_css_selector_visible(self.driver, '#user_info #authenticated', 10)
        self.driver.execute_script('Api.testMode(true);')

    def tearDown(self):
        self.driver.close()
