# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from argparse import ArgumentParser


class ResettableArgumentParser(ArgumentParser):
    """
    This class allows a parser instance to be reset to a known state, i.e.
    before certain arguments were added.  This is useful for allowing the
    same parser instance to be re-used multiple times with different
    argument sets.
    """
    def __init__(self, *args, **kwargs):
        self._resettable_actions = []
        super(ResettableArgumentParser, self).__init__(*args, **kwargs)

    def _add_action(self, action):
        self._resettable_actions.append(action)
        return super(ResettableArgumentParser, self)._add_action(action)

    def _remove_action(self, action):
        self._resettable_actions.remove(action)
        super(ResettableArgumentParser, self)._add_action(action)

    def clear_resets(self):
        """
        Clear the parser's reset stack -- any arguments added before this
        will be "frozen" into the parser (e.g. global arguments).  Any
        arguments added after this will be removed by a reset().
        """
        del(self._resettable_actions[0:])

    def reset(self):
        """
        Roll the parser back to the last known state (i.e. instantiation
        or the last clear_resets() invocation).
        """
        for action in self._resettable_actions:
            super(ResettableArgumentParser, self)._remove_action(action)
        self.clear_resets()
