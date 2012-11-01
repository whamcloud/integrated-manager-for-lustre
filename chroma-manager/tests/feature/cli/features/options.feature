Feature: CLI options should be parsed correctly
  In order to change the behavior of the CLI
  As a Chroma CLI user
  I want to supply CLI options and have them work properly

Background:
  Given the config has been reset to defaults

Scenario Outline: Options With Values
  Given the config parameter <config_key> should be set to the default
  When I run chroma <option> <value> server-list
  Then the config parameter <config_key> should be set to <value>

Examples: Long options
  | option     | value     | config_key |
  | --api_url  | foo.bar   | api_url    |
  | --username | monkeyman | username   |
  | --password | bananas   | password   |
  | --output   | yaml      | output     |

Examples: Short options
  | option | value | config_key |
  | -o     | json  | output     |

Scenario Outline: Boolean Options
  Given the config parameter <config_key> should be set to the default
  When I run chroma <option> server-list
  Then the config parameter <config_key> should be set to True

Examples: Long options
  | option    | config_key |
  | --nowait  | nowait     |
  | --noproxy | noproxy    |
  | --force   | force      |

Examples: Short options
  | option | config_key |
  | -n     | nowait     |
  | -x     | noproxy    |
  | -f     | force      |
