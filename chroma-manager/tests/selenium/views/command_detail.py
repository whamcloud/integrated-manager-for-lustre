#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base_view import BaseView
from tests.selenium.utils.element import find_visible_element_by_css_selector


class CommandDetail(BaseView):
    @property
    def visible(self):
        return find_visible_element_by_css_selector(self.driver, 'div.command_detail')
