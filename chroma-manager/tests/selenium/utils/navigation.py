#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
import datetime
from time import sleep

from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from testconfig import config

from tests.selenium.base_view import BaseView
from tests.selenium.utils.element import (
    find_visible_element_by_css_selector, wait_for_element_by_css_selector,
    wait_for_any_element_by_css_selector
)


class Navigation(BaseView):
    def __init__(self, driver):
        """
        List of clickable UI elements in menus/tabs/pages
        @param: driver - Instance of the webdriver
        """
        super(Navigation, self).__init__(driver)

        self.links = {
            # Elements in Main Menu
            'Dashboard': '#dashboard_menu',
            'Configure': '#configure_menu',
            'Alerts': '#alert_menu',
            'Events': '#event_menu',
            'Logs': '#log_menu',

            # Elements under configure tab
            'Filesystems': "a[href='#filesystem-tab']",
            'MGTs': "a[href='#mgt-tab']",
            'Volumes': "a[href='#volume-tab']",
            'Servers': "a[href='#server-tab']",
            'Storage': "a[href='#storage-tab']",
            'Users': "a[href='#user-tab']",
            'Create_new_filesystem': "#create_new_fs",
        }

        self._patch_api()

    def _patch_api(self):
        """Modify the JS behaviour to be more cooperative for
           testing -- call this after any non-ajax navigation"""
        self.quiesce()
        self.log.debug("Calling testMode")
        self.driver.execute_script('return Api.testMode(true);')
        # The fade-out of the blocking animation can still be in progress, wait for it to hide
        self.wait_for_removal("div.blockUI")

    def login(self, username, password):
        """Login with given username and password"""
        self.log.debug("Logging in %s" % username)
        from tests.selenium.views.login import Login
        wait_for_any_element_by_css_selector(self.driver, ['#login_dialog', '#user_info #anonymous #login'], 10)
        login_view = Login(self.driver)
        if not find_visible_element_by_css_selector(self.driver, '#login_dialog'):
            login_view.open_login_dialog()
        login_view.login_user(username, password)
        wait_for_element_by_css_selector(self.driver, '#username', self.medium_wait)
        self.quiesce()
        self._patch_api()

    def logout(self):
        self.log.debug("Logging out")
        self.driver.find_element_by_css_selector("#logout").click()
        wait_for_any_element_by_css_selector(self.driver, ['#login_dialog', '#user_info #anonymous #login'], 10)
        self._patch_api()

    def refresh(self):
        self.log.info("Navigation.refresh %s" % self.driver.execute_script('return window.location.href;'))
        self.driver.refresh()
        self._patch_api()
        self.quiesce()

    def reset(self):
        self.driver.get(config['chroma_managers']['server_http_url'])
        wait_for_element_by_css_selector(self.driver, '#dashboard_menu', 10)
        self._patch_api()
        self.quiesce()

    def go(self, *args):
        self.log.info("Navigation.go: %s" % (args,))
        for page in args:
            self.click(self.links[page])
        self.quiesce()

    def screenshot(self):
        if config['screenshots']:
            filename = "%s_%s.png" % (datetime.datetime.now().isoformat(), self.driver.current_url.replace("/", "_"))
            self.driver.get_screenshot_as_file(filename)

    def click(self, selector):
        """
        A generic function to click an element and wait for blockoverlay screen and jGrowl notifications
        @param: element_id - Specify the ID of the element to be clicked as seen on the UI
        """

        block_overlay_classname = "div.blockUI.blockOverlay"
        jGrowl_notification_classname = "div.jGrowl-notification.highlight.ui-corner-all.default"

        for wait_before_count in xrange(self.standard_wait):
            is_overlay = self.wait_for_loading_page(block_overlay_classname)
            is_jGrowl_notification = self.wait_for_loading_page(jGrowl_notification_classname)
            if is_overlay or is_jGrowl_notification:
                sleep(2)
            else:
                link_handle = self.driver.find_element_by_css_selector(selector)
                link_handle.click()
                for wait_after_count in xrange(self.standard_wait):
                    is_overlay = self.wait_for_loading_page(block_overlay_classname)
                    is_jGrowl_notification = self.wait_for_loading_page(jGrowl_notification_classname)
                    if is_overlay or is_jGrowl_notification:
                        sleep(2)
                        continue
                    else:
                        break
                break

    def wait_for_loading_page(self, blocking_element_class):
        try:
            blocking_div = self.driver.find_element_by_css_selector(blocking_element_class)
            try:
                if blocking_div.is_displayed():
                    return True
            except StaleElementReferenceException:
                return False
        except NoSuchElementException:
            return False
