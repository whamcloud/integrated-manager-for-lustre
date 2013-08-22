Feature: Manage Chroma Servers
  In order to manage my Chroma Servers
  As a Chroma administrator who likes using the CLI
  I want to type things into a shell to manage my servers

Background: Set up test environment
  Given the "server-management" mocks are loaded

Scenario: List server profiles
  When I run chroma server_profile-list
  Then I should see output containing "test_profile"

Scenario: Add a server without profile
  Given the server count should be 0
  And the following commands will fail
  When I run chroma server-add setup-mgs
  Then the server count should be 0
  And I should see output containing "No server_profile supplied"

Scenario: Add a server
  Given the server count should be 0
  When I run chroma server-add setup-mgs --server_profile test_profile
  Then the server count should be 1

Scenario: Stop LNet on a server
  Given the server state on setup-mgs should be lnet_up
  When I run chroma server setup-mgs lnet-stop
  Then the server state on setup-mgs should be lnet_down

Scenario: Unload LNet on a server
  Given the server state on setup-mgs should be lnet_down
  When I run chroma server setup-mgs lnet-unload
  Then the server state on setup-mgs should be lnet_unloaded

Scenario: Load LNet on a server
  Given the server state on setup-mgs should be lnet_unloaded
  When I run chroma server setup-mgs lnet-load
  Then the server state on setup-mgs should be lnet_down

Scenario: Start LNet on a server
  Given the server state on setup-mgs should be lnet_down
  When I run chroma server setup-mgs lnet-start
  Then the server state on setup-mgs should be lnet_up

Scenario: Remove a server
  Given the server count should be 1
  When I run chroma server-remove setup-mgs.lab.whamcloud.com
  #Then I should be prompted to proceed # FIXME: HYD-2409
  Then the server count should be 0

Scenario: Fail to add non-resolving server
  Given the server count should be 0
  And the resolve host contact test should fail
  When I run chroma server-add setup-mgs
  Then the server count should be 0

Scenario: Force addition of a non-pingable server
  Given the server count should be 0
  And the ping host contact test should fail
  When I run chroma --force server-add setup-mgs --server_profile test_profile
  Then the server count should be 1

Scenario: Reboot a server
  Given the server count should be 1
  And the boot_time on setup-mgs has been recorded
  When I run chroma server-reboot setup-mgs
  Then I should be prompted to proceed
  Then the boot_time on setup-mgs should reflect a reboot

Scenario: Shutdown a server
  Given the server count should be 1
  When I run chroma server-shutdown setup-mgs
  Then I should be prompted to proceed
  Then I should see output containing ": Finished"

Scenario: Force-remove a server
  Given the server count should be 1
  When I run chroma server-force_remove setup-mgs
  Then I should be prompted to proceed
  Then the server count should be 0
