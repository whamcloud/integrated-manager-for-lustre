#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base import element_visible
from tests.selenium.base_view import BaseView


class CommandDetail(BaseView):
    @property
    def visible(self):
        return element_visible(self.driver, 'div.command_detail')
