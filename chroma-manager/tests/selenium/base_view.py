
import logging
import time
from urlparse import urlparse

from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from tests.selenium.base import wait_for_transition
from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.element import find_visible_element_by_css_selector, wait_for_element_by_css_selector


log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)


class BaseView(object):
    #@FIXME: should abstract this path "/ui/" to the config file.
    path = "/ui/"

    def __init__(self, driver):
        self.driver = driver
        self.log = log

        self.long_wait = wait_time['long']
        self.medium_wait = wait_time['medium']
        self.standard_wait = wait_time['standard']
        self.short_wait = wait_time['short']

        #store selectors and selectors to be formatted.
        self.dropdown_class_name = 'dropdown'
        self.dropdown_selector = '.%s' % self.dropdown_class_name
        self.dropdown_menu_class_name = 'dropdown-menu'
        self.dropdown_menu_selector = '.%s' % self.dropdown_menu_class_name
        self.state_format = self.dropdown_menu_selector + ' a[data-state="%s"]'

    def quiesce(self):
        for i in xrange(self.long_wait):
            busy = self.driver.execute_script('return ($.active != 0);')
            animated = self.driver.execute_script('return $(":animated").length;')
            if not busy and not animated:
                self.log.debug('quiesced in %s iterations' % i)
                return
            else:
                time.sleep(1)

        raise RuntimeError("Timed out waiting for API operations to complete after %s seconds" % self.long_wait)

    def wait_for_removal(self, selector):
        """Wait for all elements matching selector to be removed from the DOM"""
        for i in xrange(self.standard_wait):
            if not len(self.driver.find_elements_by_css_selector(selector)):
                return

        raise RuntimeError("Timed out after %s waiting for %s to be removed" % (self.standard_wait, selector))

    def get_visible_element_by_css_selector(self, selector):
        """Return an element matching the selector which is visible, or raise
        an exception if no such element exists.  Useful when there is
        more than one element in the DOM matching the selector but you
        want to find the one that is currently on-screen."""

        element = find_visible_element_by_css_selector(self.driver, selector)
        if not element:
            raise RuntimeError("No visible element match %s" % selector)
        return element

    def _find_state_anchor(self, container, state):
        sel = self.state_format % state

        try:
            return container.find_element_by_css_selector(sel)
        except NoSuchElementException:
            raise NoSuchElementException("No action found with state %s" % state)

    def click_command_button(self, container, state):
        """Find the action within the dropdown that is a state transition
        to `state`, click it, and wait for the transition to complete"""

        self.quiesce()

        wait_for_element_by_css_selector(container, self.dropdown_selector, self.standard_wait)

        dropdown = container.find_element_by_class_name(self.dropdown_class_name)
        dropdown_menu = dropdown.find_element_by_class_name(self.dropdown_menu_class_name)

        if not dropdown_menu.is_displayed():
            dropdown.click()

        anchor = self._find_state_anchor(dropdown_menu, state)
        anchor.click()

        # Lets move the mouse off the button to untrigger any hover that could block
        # the #transition_confirm_button.
        ActionChains(self.driver).move_by_offset(0, -5).perform()

        self.quiesce()

        if find_visible_element_by_css_selector(self.driver, '#transition_confirm_button'):
            self.driver.find_element_by_css_selector('#transition_confirm_button').click()
            self.quiesce()
        wait_for_transition(self.driver, self.long_wait)

        try:
            anchor.is_displayed()
            if dropdown.is_displayed():
                raise RuntimeError("Transition to %s in %s failed (action still selectable)" % (state, container))
        except StaleElementReferenceException:
            pass

    def get_table_text(self, table_element, columns):
        """Given a table element, return a list of lists of values
        of specified column indices"""

        records = []
        for row in table_element.find_elements_by_css_selector('tr'):
            tds = row.find_elements_by_css_selector('td')

            record = []
            try:
                for column_idx in columns:
                    record.append(tds[column_idx].text)
            except IndexError:
                continue

            records.append(record)

        return records

    def find_row_by_column_text(self, table, col_id_to_text):
        """Find a tr element within a table element which matches
        a map of column indices to column text"""

        rows = table.find_elements_by_css_selector("tr")
        for tr in rows:
            tds = tr.find_elements_by_css_selector("td")
            match = True
            for col_id, text in col_id_to_text.items():
                try:
                    if tds[col_id].text != text:
                        match = False
                except IndexError:
                    match = False
            if match:
                return tr

        raise NoSuchElementException("No match for %s in %s rows of table %s: %s" % (
            col_id_to_text, len(rows), table, self.get_table_text(table, col_id_to_text.keys())))

    def volume_chooser_open_and_select(self, chooser_id, server_address, volume_name, multi = False):
        """Click storage button and select an MGT from chooser"""
        chooser_button = self.driver.find_element_by_css_selector("#%s_outer" % chooser_id)
        chooser_button.click()
        self.quiesce()
        self.volume_chooser_select(chooser_id, server_address, volume_name, multi)

    def volume_chooser_select(self, chooser_id, server_address, volume_name, multi):
        table = self.driver.find_element_by_css_selector("table#%s_table" % chooser_id)
        if multi:
            # Multi-selectable volume choosers have an extra column at 0 with a checkbox in
            row = self.find_row_by_column_text(table, {5: server_address, 1: volume_name})
        else:
            row = self.find_row_by_column_text(table, {4: server_address, 0: volume_name})
        row.click()
        self.quiesce()

    def get_input_error(self, input_element):
        """Given an input element, get the validation error text attached to it, or
        raise an exception if it does not have a validation error"""

        parent = input_element.find_element_by_xpath("..")
        try:
            return parent.find_element_by_css_selector("span.error").text
        except NoSuchElementException:
            return None

    def _get_url_parts(self):
        return list(urlparse(self.driver.current_url))

    def on_page(self, path=None):
        if not path:
            path = self.path

        parts = self._get_url_parts()

        return parts[2].endswith(path)

    def patch_api(self):
        """Modify the JS behaviour to be more cooperative for
           testing -- call this after any non-ajax navigation"""
        self.quiesce()
        self.log.debug("Calling testMode")
        self.driver.execute_script('return Api.testMode(true);')
        # The fade-out of the blocking animation can still be in progress, wait for it to hide
        self.wait_for_removal("div.blockUI")

    def wait_for_angular(self):
        """
            Puts Angular in a usable state by executing all poll functions
            and making sure the http queue is clear.
        """

        script = """
            var callback = arguments[arguments.length - 1];

            angular.element(document.body).injector().get('$browser').
            notifyWhenNoOutstandingRequests(callback);
        """

        return self.driver.execute_async_script(script)

    def test_for_angular(self):
        """
            Waits for Angular to be available.
        """

        script = """
            var callback = arguments[arguments.length - 1];
            var retry = function(n) {
                if (window.angular && window.angular.resumeBootstrap) {
                    callback(true);
                } else if (n < 1) {
                    callback(false);
                } else {
                    window.setTimeout(function() {retry(n - 1)}, 1000);
                }
            };

            if (window.angular && window.angular.resumeBootstrap) {
                callback(true);
            } else {
                retry(3);
            }
        """

        return self.driver.execute_async_script(script)

    def disable_css3_transitions(self):
        """
            Adds a style rule to the DOM disabling all css3 transitions.
        """

        script = """
            var css = document.createElement('style');
            css.type = 'text/css';
            css.innerHTML = '* {-webkit-transition: none !important; -moz-transition: none !important; -o-transition: none !important; transition: none !important;}';
            document.body.appendChild(css);
        """

        self.driver.execute_script(script)

    def _reset_ui(self, angular_only=False):
        self.test_for_angular()
        self.wait_for_angular()
        self.disable_css3_transitions()

        if not angular_only:
            self.patch_api()
            self.quiesce()


class DatatableView(BaseView):
    datatable_id = None
    label_column = 0

    @property
    def datatable(self):
        return self.driver.find_element_by_css_selector("table#%s" % self.datatable_id)

    def _is_datatables_empty_row(self, tr):
        tds = tr.find_elements_by_tag_name("td")
        if len(tds) == 1 and 'dataTables_empty' in tds[0].get_attribute('class').split():
            return True
        else:
            return False

    @property
    def rows(self):
        rows = self.driver.find_elements_by_xpath("id('" + self.datatable_id + "')/tbody/tr")

        # datatables uses one 'row' to represent an empty table, catch that and return an
        # empty list instead
        if len(rows) == 1:
            if self._is_datatables_empty_row(rows[0]):
                return []

        return rows

    @property
    def first_row(self):
        """Return one tr element or None"""
        try:
            tr = self.driver.find_element_by_css_selector("#%s" % self.datatable_id).find_element_by_css_selector("tbody tr:first-child")
        except NoSuchElementException:
            return None

        if self._is_datatables_empty_row(tr):
            return None
        else:
            return tr

    def transition_by_column_values(self, column_values, state):
        row = self.find_row_by_column_text(self.datatable, column_values)
        self.click_command_button(row, state)

    def remove_all(self):
        self.log.info("Removing %s rows in table #%s" % (len(self.rows), self.datatable_id))
        # Can't iterate over rows because rows get deleted as objects
        # get deleted: have to do a while loop and delete rows[0] until
        # none are left.
        row = self.first_row
        while row:
            prev_id = row.id
            label = row.find_elements_by_tag_name("td")[self.label_column].text
            self.log.info("Removing object %s" % label)
            self.click_command_button(row, 'removed')
            row = self.first_row
            if row and row.id == prev_id:
                raise StaleElementReferenceException("The element %s hasn't been removed" % row.text)
