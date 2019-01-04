# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from argparse import ArgumentParser, HelpFormatter, Action


# http://hg.python.org/cpython/rev/4c0426261148/
class _AliasedChoicesPseudoAction(Action):
    def __init__(self, name, aliases, help):
        metavar = dest = name
        if aliases:
            metavar += " (%s)" % ", ".join(aliases)
        sup = super(_AliasedChoicesPseudoAction, self)
        sup.__init__(option_strings=[], dest=dest, help=help, metavar=metavar)


def _add_aliased_parser(self, name, **kwargs):
    # set prog from the existing prefix
    if kwargs.get("prog") is None:
        kwargs["prog"] = "%s %s" % (self._prog_prefix, name)

    aliases = kwargs.pop("aliases", ())

    # create a pseudo-action to hold the choice help
    if "help" in kwargs:
        help = kwargs.pop("help")
        choice_action = _AliasedChoicesPseudoAction(name, aliases, help)
        self._choices_actions.append(choice_action)

    # create the parser and add it to the map
    parser = self._parser_class(**kwargs)
    self._name_parser_map[name] = parser

    # make parser available under aliases also
    for alias in aliases:
        self._name_parser_map[alias] = parser

    return parser


# monkey-patch in our hacked add_parser() method
import argparse

argparse._SubParsersAction.add_parser = _add_aliased_parser


class ChromaHelpFormatter(HelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    --long, -s ARGS

            # Don't duplicate ARGS for --long, -s (mjmac)
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                parts.append("%s %s" % (", ".join(action.option_strings), args_string))

            return ", ".join(parts)


class ResettableArgumentParser(ArgumentParser):
    """
    This class allows a parser instance to be reset to a known state, i.e.
    before certain arguments were added.  This is useful for allowing the
    same parser instance to be re-used multiple times with different
    argument sets.
    """

    def __init__(self, *args, **kwargs):
        kwargs["formatter_class"] = ChromaHelpFormatter
        self._resettable_actions = []
        super(ResettableArgumentParser, self).__init__(*args, **kwargs)

    def add_subparsers(self, **kwargs):
        action = super(ResettableArgumentParser, self).add_subparsers(**kwargs)
        self._resettable_actions.append(action)
        return action

    def _add_action(self, action):
        self._resettable_actions.append(action)
        return super(ResettableArgumentParser, self)._add_action(action)

    def _remove_action(self, action):
        super(ResettableArgumentParser, self)._remove_action(action)
        action.container._group_actions.remove(action)
        for option_string in action.option_strings:
            del (self._option_string_actions[option_string])

    def clear_resets(self):
        """
        Clear the parser's reset stack -- any arguments added before this
        will be "frozen" into the parser (e.g. global arguments).  Any
        arguments added after this will be removed by a reset().
        """
        del (self._resettable_actions[0:])

    def reset(self):
        """
        Roll the parser back to the last known state (i.e. instantiation
        or the last clear_resets() invocation).
        """
        for action in self._resettable_actions[:]:
            self._remove_action(action)
            self._resettable_actions.remove(action)
