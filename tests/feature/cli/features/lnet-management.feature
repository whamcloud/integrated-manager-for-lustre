Feature: Manage Chroma Servers
  In order to manage my Chroma Servers
  As a Chroma administrator who likes using the CLI
  I want to type things into a shell to manage my servers

Background: Set up test environment
  Given the "server-management" mocks are loaded

Scenario: Add a server
  Given the server count should be 0
  When I run chroma server-add setup-mgs --server_profile test_profile
  Then the server count should be 1

Scenario: Stop LNet on a server
  Given the lnet_configuration state on setup-mgs should be lnet_up
  When I run chroma lnet_configuration setup-mgs lnet-stop
  Then the lnet_configuration state on setup-mgs should be lnet_down

Scenario: Unload LNet on a server
  Given the lnet_configuration state on setup-mgs should be lnet_down
  When I run chroma lnet_configuration setup-mgs lnet-unload
  Then the lnet_configuration state on setup-mgs should be lnet_unloaded

Scenario: Load LNet on a server
  Given the lnet_configuration state on setup-mgs should be lnet_unloaded
  When I run chroma lnet_configuration setup-mgs lnet-load
  Then the lnet_configuration state on setup-mgs should be lnet_down

Scenario: Remove a server
  Given the server count should be 1
  When I run chroma server-remove setup-mgs.lab.whamcloud.com
  #Then I should be prompted to proceed # FIXME: HYD-2409
  Then the server count should be 0
