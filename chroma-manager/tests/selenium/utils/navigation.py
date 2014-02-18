from time import sleep

from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from testconfig import config

from tests.selenium.base_view import BaseView
from tests.selenium.views.login import Login

from tests.selenium.utils.element import wait_for_element_by_css_selector


class Navigation(BaseView):
    def __init__(self, driver, needs_patching=True):
        """
        List of clickable UI elements in menus/tabs/pages
        @param driver: Instance of the webdriver
        @param needs_patching: Should the api be patched (not needed for new code).
        """
        super(Navigation, self).__init__(driver)

        self.links = {
            # Elements in Main Menu
            'Dashboard': '#dashboard-menu',
            'Configure': '.dropdown-toggle',
            'Alerts': '#alert-menu',
            'Events': '#event-menu',
            'Logs': '#log-menu',

            # Elements under configure tab
            'Filesystems': "a#filesystem-conf-item",
            'MGTs': "a#mgt-conf-item",
            'Volumes': "a#volume-conf-item",
            'Servers': "a#server-conf-item",
            'Storage': "a#storage-conf-item",
            'Users': "a#user-conf-item",
            'Create_new_filesystem': "#create_new_fs",
        }

        if needs_patching:
            self.patch_api()

    @property
    def configure_dropdown(self):
        return self.driver.find_element_by_css_selector(".navbar .dropdown-menu")

    def login(self, username, password):
        login = Login(self.driver)

        login.go_to_page().login_and_accept_eula_if_presented(username, password)

    def logout(self):
        login = Login(self.driver)
        login.logout()

    def refresh(self, angular_only=False):
        self.log.info("Navigation.refresh %s" % self.driver.execute_script('return window.location.href;'))
        self.driver.refresh()
        self._reset_ui(angular_only)

    def reset(self):
        self.driver.get(config['chroma_managers'][0]['server_http_url'])
        wait_for_element_by_css_selector(self.driver, '#dashboard-menu', 10)
        self._reset_ui()

    def go(self, *args):
        self.log.info("Navigation.go: %s" % (args,))

        if self.configure_dropdown.is_displayed():
            self.click(self.links['Configure'])

        for page in args:
            self.click(self.links[page])
        self._reset_ui()

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
        self.quiesce()

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
