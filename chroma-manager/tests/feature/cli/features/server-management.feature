Feature: Manage Chroma Servers
  In order to manage my Chroma Servers
  As a Chroma administrator who likes using the CLI
  I want to type things into a shell to manage my servers

Background: Set up test environment
  Given the "server-management" mocks are loaded

Scenario: Add a server
  Given the server count should be 0
  When I run chroma --username debug --password chr0m4_d3bug server-add setup-mgs
  Then the server count should be 1

Scenario: Stop LNet on a server
  Given the server state on setup-mgs should be lnet_up
  When I run chroma --username debug --password chr0m4_d3bug server setup-mgs lnet-stop
  Then the server state on setup-mgs should be lnet_down

Scenario: Unload LNet on a server
  Given the server state on setup-mgs should be lnet_down
  When I run chroma --username debug --password chr0m4_d3bug server setup-mgs lnet-unload
  Then the server state on setup-mgs should be lnet_unloaded

Scenario: Load LNet on a server
  Given the server state on setup-mgs should be lnet_unloaded
  When I run chroma --username debug --password chr0m4_d3bug server setup-mgs lnet-load
  Then the server state on setup-mgs should be lnet_down

Scenario: Start LNet on a server
  Given the server state on setup-mgs should be lnet_down
  When I run chroma --username debug --password chr0m4_d3bug server setup-mgs lnet-start
  Then the server state on setup-mgs should be lnet_up

Scenario: Remove a server
  Given the server count should be 1
  When I run chroma --username debug --password chr0m4_d3bug server-remove setup-mgs.lab.whamcloud.com
  Then the server count should be 0
