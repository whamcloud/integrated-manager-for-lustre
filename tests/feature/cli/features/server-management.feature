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
