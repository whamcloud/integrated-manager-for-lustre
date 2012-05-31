Feature: Set up new Chroma filesystem
  In order to set up a new filesystem
  As a Chroma administrator who likes using the CLI
  I want to type things into a shell and wind up with a filesystem

Background: Set up test environment
  Given the "setup-testing" mocks are loaded

Scenario: Add a server
  Given the server count should be 0
  When I run chroma --username debug --password chr0m4_d3bug server-add setup-mgs.lab.whamcloud.com
  Then the server count should be 1
