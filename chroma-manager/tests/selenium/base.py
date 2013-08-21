import datetime
import logging
import os
import shutil
import sys
import time

from django.utils.unittest import TestCase
from selenium import webdriver
from testconfig import config

from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.element import find_visible_element_by_css_selector


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

# The location of the chrome profiles depending on OS
CHROME_USER_DATA_DIR_LOC_LINUX = os.path.join(os.path.expanduser('~'), ".config/")
CHROME_USER_DATA_DIR_LOC_OSX = os.path.join(os.path.expanduser('~'), "Library/Application Support/Google/")

# The Chrome profile to use/create for running selenium tests.
# We don't want to use the Default profile as then devs can't
# have their regular browser open at the same time as running
# selenium tests.
CHROME_TEST_PROFILE = "ChromeChromaTest"


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
        if not config['chroma_managers'][0]['server_http_url']:
            raise RuntimeError("Please set server_http_url in config file")

        if config['headless']:
            from pyvirtualdisplay import Display
            display = Display(visible = 0, size = (1280, 1024))
            display.start()

        if not self.driver:
            browser = config['chroma_managers'][0]['browser']
            if browser == 'Chrome':
                options = webdriver.ChromeOptions()
                options.add_argument('no-proxy-server')

                options.add_argument('enable-crash-reporter')
                options.add_argument('full-memory-crash-report')
                options.add_argument('enable-logging=stderr')
                options.add_argument('log-level=""')  # log-level interferes with v=1
                options.add_argument('v=1000')  # Get all levels of vlogs

                if os.path.exists(CHROME_USER_DATA_DIR_LOC_LINUX):
                    options.add_argument('user-data-dir=%s' % os.path.join(CHROME_USER_DATA_DIR_LOC_LINUX, CHROME_TEST_PROFILE))
                elif os.path.exists(CHROME_USER_DATA_DIR_LOC_OSX):
                    options.add_argument('user-data-dir=%s' % os.path.join(CHROME_USER_DATA_DIR_LOC_OSX, CHROME_TEST_PROFILE))
                else:
                    raise RuntimeError(
                        "Did not find the expected location for Chrome profiles at either '%s' or '%s'" % (
                            CHROME_USER_DATA_DIR_LOC_LINUX,
                            CHROME_USER_DATA_DIR_LOC_OSX
                        )
                    )
                options.add_argument('incognito')  # To clear state between test runs since sharing a profile now

                self.driver = getattr(webdriver, browser)(chrome_options=options)
            elif browser == 'Firefox':
                self.driver = webdriver.Firefox()

        self.driver.get(config['chroma_managers'][0]['server_http_url'])

        self.addCleanup(self.stop_driver)
        self.addCleanup(self._take_screenshot_on_failure)
        self.addCleanup(self._capture_browser_log_on_failure)

        self.driver.set_script_timeout(90)

        from tests.selenium.utils.navigation import Navigation
        self.navigation = Navigation(self.driver, False)

        superuser_present = False
        for user in config['chroma_managers'][0]['users']:
            if user['is_superuser']:
                self.navigation.login(user['username'], user['password'])
                superuser_present = True
        if not superuser_present:
            raise RuntimeError("No superuser in config file")

        self.clear_all()

    def stop_driver(self):
        # It can be handy not to clean up after a failed test when a developer
        # is actively working on a test or troubleshooting a test failure and
        # to leave the browser window open. To provide for this, there is an
        # option in the config, clean_up_on_failure, that controls clean up on
        # failed tests. Cleanup will always occur for successful tests.
        # Beware that the un-cleaned-up tests will leave resources and processes
        # on your system that will not automatically be cleaned up.
        test_failed = False if sys.exc_info() == (None, None, None) else True
        if config.get("clean_up_on_failure"):
            self.log.info("Quitting driver after %s" % "failure" if test_failed else "success")
            self.driver.quit()
        elif not test_failed:
            self.log.info("Closing driver after success")
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
        for user in config['chroma_managers'][0]['users']:
            if user['is_superuser']:
                superuser_username = user['username']
        if not superuser_username:
            raise RuntimeError("Test config does not define a superuser")
        else:
            self.navigation.go('Configure', 'Users')
            Users(self.driver).delete_all_except(superuser_username)

    def volume_and_server(self, index, lustre_server = None):
        if not lustre_server:
            lustre_server = config['lustre_servers'][0]['nodename']

        server_config = None
        for server in config['lustre_servers']:
            if server['nodename'] == lustre_server:
                server_config = server
        if not server_config:
            raise RuntimeError("No lustre server found called '%s'" % lustre_server)

        volume = server_config['device_paths'][index]
        volume_label = config['device_path_to_label_map'][volume]

        return volume_label, server_config['nodename']

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

        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')
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

    def _take_screenshot_on_failure(self):
        test_failed = False if sys.exc_info() == (None, None, None) else True

        if config['screenshots'] and test_failed:
            failed_screen_shot_dir = "%s/failed-screen-shots" % os.getcwd()

            if not os.path.exists(failed_screen_shot_dir):
                os.makedirs(failed_screen_shot_dir)

            filename = "%s/%s_%s.png" % (
                failed_screen_shot_dir,
                self.id(),
                datetime.datetime.now().isoformat()
            )

            self.log.debug("Saving screen shot to %s", filename)
            self.driver.get_screenshot_as_file(filename)

    def _capture_browser_log_on_failure(self):
        test_failed = False if sys.exc_info() == (None, None, None) else True

        if test_failed and config['chroma_managers'][0]['browser'] == 'Chrome':
            failed_browser_log_dir = os.path.join(os.getcwd(), 'failed-browser-logs')

            if not os.path.exists(failed_browser_log_dir):
                os.makedirs(failed_browser_log_dir)

            filename = os.path.join(
                failed_browser_log_dir,
                "%s_%s_chrome_debug.log" % (
                    self.id(),
                    datetime.datetime.now().isoformat()
                )
            )

            self.log.debug("Saving log file to %s" % filename)
            try:
                shutil.copy(os.path.join(CHROME_USER_DATA_DIR_LOC_LINUX, CHROME_TEST_PROFILE, "chrome_debug.log"), filename)
            except:
                try:
                    shutil.copy(os.path.join(CHROME_USER_DATA_DIR_LOC_OSX, CHROME_TEST_PROFILE, "chrome_debug.log"), filename)
                except:
                    raise RuntimeError("Did not find Chrome user-data-dir in the expected location.")
