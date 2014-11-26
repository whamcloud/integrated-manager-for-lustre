#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from selenium.common.exceptions import NoSuchElementException


class SelectBoxIt(object):
    def __init__(self, driver, select_container):
        self.driver = driver
        self.select_container = select_container

    @property
    def select(self):
        return self.select_container.find_element_by_class_name(self.SELECT_CLASS)

    @property
    def options(self):
        return self.select_container.find_elements_by_class_name(self.OPTION_CLASS)

    @property
    def selected_option(self):
        return self.select_container.find_element_by_css_selector('.%s .%s' % (
            self.SELECTED_OPTION_CLASS, self.OPTION_CLASS
        ))

    CONTAINER_SELECTOR = 'td > .selectboxit-container'
    SELECT_CLASS = 'selectboxit'
    DISABLED_SELECT_CLASS = 'selectboxit-disabled'
    OPTIONS_CONTAINER_CLASS = 'selectboxit-options'
    OPTION_CLASS = 'selectboxit-option-anchor'
    SELECTED_OPTION_CLASS = 'selectboxit-selected'

    BLANK_OPTION_TEXT = '---'

    def click_select(self):
        self.select.click()

    def open_and_close(self, fn):
        self.click_select()

        result = fn()

        self.click_select()

        return result

    def get_options_text(self):
        return self.open_and_close(lambda: [option.text for option in self.options])

    def has_option(self, option_text):
        return option_text in self.get_options_text()

    def is_selected(self, option_text):
        return self.open_and_close(lambda: self.selected_option.text == option_text)

    def get_selected(self):
        return self.open_and_close(lambda: self.selected_option.text)

    def select_option(self, option_text):
        """Selects an option in the Select Box.

        :param option_text: string
        :raises: RuntimeError
        """
        self.click_select()

        try:
            option = next(option for option in self.options if option.text == option_text)
            option.click()

        except StopIteration:

            texts = [element.text for element in self.options]

            msg = '### Select box contains: [{0}], we wanted: [{1}]'.format(' '.join(texts), option_text)

            raise RuntimeError(msg)

    def is_disabled(self):
        try:
            self.select_container.find_element_by_class_name(self.DISABLED_SELECT_CLASS)
            return True
        except NoSuchElementException:
            return False
