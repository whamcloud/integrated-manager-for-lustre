#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base_view import DatatableView
from tests.selenium.utils.constants import static_text
from tests.selenium.utils.element import (
    enter_text_for_element, find_visible_element_by_css_selector,
    select_element_option, wait_for_element_by_css_selector,
    wait_for_element_by_xpath
)


class Users(DatatableView):
    datatable_id = "user_list"
    label_column = 0

    def __init__(self, driver):
        super(Users, self).__init__(driver)

        # Initialise elements on this page
        self.create_new_user_button = self.driver.find_element_by_css_selector("#create_user")
        self.create_user_dialog = "div.create_user_dialog"
        self.user_detail = "div.user_detail div.tabs"
        self.user_details_tab = '%s a[href="#user_details_tab"]' % self.user_detail
        self.user_details_panel = '%s div#user_details_tab' % self.user_detail
        self.user_password_tab = '%s a[href="#user_password_tab"]' % self.user_detail
        self.user_password_panel = '%s div#user_password_tab' % self.user_detail
        self.user_alerts_tab = '%s a[href="#user_alert_subs_tab"]' % self.user_detail
        self.user_alerts_panel = '%s div#user_alert_subs_tab' % self.user_detail
        self.user_alerts_form = '%s ul#user_alerts_form' % self.user_alerts_panel
        self.update_alerts_button = "button.update_subscriptions"
        self.all_alerts_button = "button.select_all_subscriptions"
        self.no_alerts_button = "button.clear_subscriptions"

        self.delete_user_dialog = "div.delete_user_dialog"

        self.user_group = "div.create_user_dialog select"
        self.username = "div.create_user_dialog input[name=username]"
        self.first_name = "div.create_user_dialog input[name=first_name]"
        self.last_name = "div.create_user_dialog input[name=last_name]"
        self.email = "div.create_user_dialog input[name=email]"
        self.password1 = "div.create_user_dialog input[name=password1]"
        self.password2 = "div.create_user_dialog input[name=password2]"
        self.create_user_button = "button.create_button"

        self.edit_email = "%s input[name=email]" % self.user_details_panel
        self.edit_first_name = "%s input[name=first_name]" % self.user_details_panel
        self.edit_last_name = "%s input[name=last_name]" % self.user_details_panel
        self.edit_save_button = "button.save_user"

        self.old_password = "%s input[name=old_password]" % self.user_password_panel
        self.edit_password1 = "%s input[name=new_password1]" % self.user_password_panel
        self.edit_password2 = "%s input[name=new_password2]" % self.user_password_panel
        self.change_password_button = "button.change_password"

        self.delete_button = "button.delete_button"

        self.error_span = "span.error"
        self.user_list_datatable = 'user_list'
        self.username_td = 0
        self.user_group_td = 3

    def add(self, user_group, username, first_name, last_name, email, password, confirm_password):
        # Enter data for adding new user

        select_element_option(self.driver, self.user_group, user_group)
        enter_text_for_element(self.driver, self.username, username)
        enter_text_for_element(self.driver, self.first_name, first_name)
        enter_text_for_element(self.driver, self.last_name, last_name)
        enter_text_for_element(self.driver, self.email, email)
        enter_text_for_element(self.driver, self.password1, password)
        enter_text_for_element(self.driver, self.password2, confirm_password)

        # Click create button
        self.driver.find_element_by_css_selector(self.create_user_button).click()
        self.quiesce()

    def edit(self, username, email, first_name, last_name):
        # Edit user details
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['edit_user']:
                button.click()
                wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
                enter_text_for_element(self.driver, self.edit_email, email)
                enter_text_for_element(self.driver, self.edit_first_name, first_name)
                enter_text_for_element(self.driver, self.edit_last_name, last_name)
                # Click save button
                self.driver.find_element_by_css_selector(self.edit_save_button).click()
                wait_for_element_by_xpath(self.driver, '//div[@id="user_save_result"][contains(., "Changes saved successfully.")]', self.medium_wait)
                # Click close button
                self.driver.find_element_by_css_selector('button.close').click()
                assert not find_visible_element_by_css_selector(self.driver, self.user_detail)
                self.quiesce()
                return

        raise RuntimeError("Cannot edit user with username " + username)

    def change_password(self, username, new_password, new_confirm_password):
        # Change user password
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['edit_user']:
                button.click()
                wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
                self.driver.find_element_by_css_selector(self.user_password_tab).click()
                enter_text_for_element(self.driver, self.edit_password1, new_password)
                enter_text_for_element(self.driver, self.edit_password2, new_confirm_password)
                # Click save button
                self.driver.find_element_by_css_selector(self.change_password_button).click()
                # Click close button
                self.driver.find_element_by_css_selector('button.close').click()
                self.quiesce()
                return

        raise RuntimeError("Cannot change password for user: %s" + username)

    def edit_alerts(self, username, alert_subscriptions):
        # Change user's alert subscriptions
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['edit_user']:
                button.click()
                wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
                self.driver.find_element_by_css_selector(self.user_alerts_tab).click()
                alerts_form = self.driver.find_element_by_css_selector(self.user_alerts_form)
                self._fill_out_alerts_form(alerts_form, alert_subscriptions)

                # Click save button
                self.driver.find_element_by_css_selector(self.update_alerts_button).click()
                # Click close button
                self.driver.find_element_by_css_selector('button.close').click()
                self.quiesce()
                return

        raise RuntimeError("Cannot edit alerts for user: %s" + username)

    def delete(self, username):
        # Delete user
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['delete_user']:
                button.click()
                self.quiesce()
                wait_for_element_by_css_selector(self.driver, self.delete_user_dialog, self.medium_wait)
                # Click delete button
                self.driver.find_element_by_css_selector(self.delete_button).click()
                return

        raise RuntimeError("Failed to find delete button for user %s" % username)

    def delete_all_except(self, protect_username):
        usernames = [row[0] for row in self.get_table_text(self.datatable, [self.username_td])]
        for username in [u for u in usernames if u != protect_username]:
            self.log.debug("Removing user %s" % username)
            self.delete(username)

    def locate_user(self, username):
        return self.find_row_by_column_text(self.datatable, {self.username_td: username})

    def edit_own_password(self, password, new_password):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        self.driver.find_element_by_css_selector(self.user_password_tab).click()
        enter_text_for_element(self.driver, self.old_password, password)
        enter_text_for_element(self.driver, self.edit_password1, new_password)
        enter_text_for_element(self.driver, self.edit_password2, new_password)
        # Click save button
        self.driver.find_element_by_css_selector(self.change_password_button).click()
        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

    def edit_own_details(self, username, email, first_name, last_name):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        enter_text_for_element(self.driver, self.edit_email, email)
        enter_text_for_element(self.driver, self.edit_first_name, first_name)
        enter_text_for_element(self.driver, self.edit_last_name, last_name)
        # Click save button
        self.driver.find_element_by_css_selector(self.edit_save_button).click()
        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

    def list_own_subscribed_alerts(self):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        self.driver.find_element_by_css_selector(self.user_alerts_tab).click()
        alerts_form = self.driver.find_element_by_css_selector(self.user_alerts_form)
        subscribed = [el.get_attribute('name') for el in alerts_form.find_elements_by_css_selector('input[type="checkbox"]') if el.is_selected()]

        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

        return subscribed

    def subscribe_to_no_alerts(self):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        self.driver.find_element_by_css_selector(self.user_alerts_tab).click()

        # Click select all button
        self.driver.find_element_by_css_selector(self.no_alerts_button).click()
        # Click save button
        self.driver.find_element_by_css_selector(self.update_alerts_button).click()
        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

    def subscribe_to_all_alerts(self):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        self.driver.find_element_by_css_selector(self.user_alerts_tab).click()

        # Click select all button
        self.driver.find_element_by_css_selector(self.all_alerts_button).click()
        # Click save button
        self.driver.find_element_by_css_selector(self.update_alerts_button).click()
        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

    def _fill_out_alerts_form(self, alerts_form, user_subscriptions):
        for checkbox in alerts_form.find_elements_by_css_selector('input[type="checkbox"]'):
            if checkbox.get_attribute('name') in user_subscriptions:
                # If it's supposed to be checked
                if not checkbox.is_selected():
                    # ... and it's not, click it.
                    checkbox.click()
            else:
                # If it's not supposed to be checked
                if checkbox.is_selected():
                    # ... and it is, click it.
                    checkbox.click()

    def edit_own_subscribed_alerts(self, user_subscriptions):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        wait_for_element_by_css_selector(self.driver, self.user_detail, self.medium_wait)
        self.driver.find_element_by_css_selector(self.user_alerts_tab).click()
        alerts_form = self.driver.find_element_by_css_selector(self.user_alerts_form)
        self._fill_out_alerts_form(alerts_form, user_subscriptions)

        # Click save button
        self.driver.find_element_by_css_selector(self.update_alerts_button).click()
        # Click close button
        self.driver.find_element_by_css_selector('button.close').click()
        self.quiesce()

    @property
    def edit_dialog_visible(self):
        return self.driver.find_element_by_css_selector(self.edit_user_dialog).is_displayed()

    @property
    def username_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.username))

    @property
    def password_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.password1))

    @property
    def password2_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.password2))

    def creation_dialog_close(self):
        self.get_visible_element_by_css_selector(".cancel_button").click()
        assert not find_visible_element_by_css_selector(self.driver, self.create_user_dialog)
