""" This is a dict for all message texts
"""


class Messages:
    def __init__(self):
        self.messages = {
            "file_systemname_blank": "Please enter valid File system name",
            "mgt_not_selected": "You must choose an MGT",
            "mdt_not_selected": "You must choose an MDT",
            "ost_not_selected": "Please select at least one device for OST creation",
            "stop_action_text": "Stop",
            "start_action_text": "Start",
            "remove_action_text": "Remove",
        }

    def get_message(self, action):
        return self.messages[action]
