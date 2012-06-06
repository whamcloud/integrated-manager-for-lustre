#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import time

# Import third-party modules
from selenium import webdriver
from views.login import Login
from django.utils.unittest import TestCase
from utils.constants import wait_time
from testconfig import config
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from utils.navigation import Navigation
from selenium.webdriver.support.ui import WebDriverWait


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
            return True

        time.sleep(1)
    raise RuntimeError('Timeout while waiting for an element to get visible')


def wait_for_any_element(driver, selectors, timeout):
    for i in xrange(timeout):
        for s in selectors:
            if element_visible(driver, s):
                return True

        time.sleep(1)
    raise RuntimeError('Timeout while waiting for an array of elements to get visible')


def wait_for_screen_unblock(driver, timeout):
    WebDriverWait(driver, timeout).until(lambda driver: driver.find_element_by_css_selector("div.blockUI.blockOverlay").is_displayed())

    try:
        block_element = driver.find_element_by_css_selector("div.blockUI.blockOverlay")
        try:
            WebDriverWait(driver, timeout).until(lambda driver: not block_element.is_displayed())
        except StaleElementReferenceException:
            return
    except NoSuchElementException:
        return


def wait_for_transition(driver, timeout):
    # Wait for transition (i.e busy/locked) icon to get displayed
    busy_icon_check = False

    WebDriverWait(driver, timeout).until(lambda driver: driver.find_element_by_css_selector("span.notification_object_icon.busy_icon").is_displayed() or driver.find_element_by_css_selector("span.notification_object_icon.locked_icon").is_displayed())

    try:
        if driver.find_element_by_css_selector("span.notification_object_icon.busy_icon").is_displayed():
            busy_icon_check = True
    except NoSuchElementException:
        pass

    for timer in xrange(timeout):
        # Wait while the transition is in progress
        try:
            # Check for which icon to wait for to get displayed
            busy_icon = None
            locked_icon = None
            if busy_icon_check:
                busy_icon = driver.find_element_by_css_selector("span.notification_object_icon.busy_icon")
            else:
                locked_icon = driver.find_element_by_css_selector("span.notification_object_icon.locked_icon")
            try:
                if busy_icon_check:
                    if busy_icon.is_displayed():
                        time.sleep(2)
                        continue
                else:
                    if locked_icon.is_displayed():
                        time.sleep(2)
                        continue
            except StaleElementReferenceException:
                return
        except NoSuchElementException:
            return

    raise RuntimeError('Timeout while waiting for transition to get complete')


def enter_text_for_element(driver, selector, text_value):
    element = driver.find_element_by_css_selector(selector)
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


def wait_for_datatable(driver, selector, timeout = 10):
    # A loaded datatable always has at least one tr, either
    # a real record or a "no data found" row
    WebDriverWait(driver, 15).until(lambda driver: driver.find_element_by_class_name("dataTables_processing").is_displayed() == False)
    wait_for_element(driver, selector + " tbody tr", timeout)


def quiesce_api(driver, timeout):
    for i in xrange(timeout):
        busy = driver.execute_script('Api.busy();')
        if not busy:
            return
    raise RuntimeError('Timeout')


def login(driver, username, password):
    """Login with given username and password"""
    wait_for_any_element(driver, ['#login_dialog', '#user_info #anonymous #login'], 10)
    login_view = Login(driver)
    if not element_visible(driver, '#login_dialog'):
        login_view.open_login_dialog()
    login_view.login_user(username, password)


class SeleniumBaseTestCase(TestCase):
    """This is the base class for the test classes.
    The setUp() method is called during the
    initialization process. The tearDown() method is called
    irrespective of the status of the application.
    """
    driver = None

    test_logger = logging.getLogger(__name__)
    test_logger.addHandler(logging.StreamHandler())
    test_logger.setLevel(logging.INFO)

    def setUp(self):

        if config['chroma_managers']['headless']:
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
        self.driver.execute_script('Api.testMode(true);')
        self.navigation = Navigation(self.driver)

    def tearDown(self):
        self.driver.close()
