Feature: Manage Chroma filesystems
  In order to manage my filesystem
  As an administrator who likes using the CLI
  I want to type things into a shell to manage my filesystem

Background: Set up test environment
  Given the "filesystem-management" mocks are loaded
  And the mock servers are set up

Scenario: Create new filesystem
  Given the filesystem count should be 0
  When I run chroma filesystem-add ohbehave --mgt setup-mgs:/fake/path/2 --mdt setup-mds:/fake/path/1 --ost setup-oss0:/fake/path/3 --ost setup-oss1:/fake/path/4
  Then the filesystem count should be 1
  And the target count should be 4
  And the ost count should be 2

