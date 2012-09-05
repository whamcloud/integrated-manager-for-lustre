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

Scenario: Stop an available filesystem
  Given the filesystem state on ohbehave should be available
  When I run chroma filesystem-stop ohbehave
  Then the filesystem state on ohbehave should be stopped

Scenario: Start a stopped filesystem
  Given the filesystem state on ohbehave should be stopped
  When I run chroma filesystem-start ohbehave
  Then the filesystem state on ohbehave should be available

Scenario: Remove filesystem
  Given the filesystem count should be 1
  When I run chroma filesystem-remove ohbehave
  Then the filesystem count should be 0
  And the ost count should be 0
  And the mdt count should be 0
  But the mgt count should be 1

Scenario: Remove lingering MGT
  Given the mgt count should be 1
  When I run chroma mgt-remove MGS
  Then the mgt count should be 0

Scenario: Create a standalone MGS
  Given the mgt count should be 0
  When I run chroma mgt-add setup-mgs:/fake/path/2
  Then the mgt count should be 1

Scenario: Create new filesystem with existing MGT
  Given the mgt count should be 1
  And the filesystem count should be 0
  When I run chroma filesystem-add behave1 --mgt setup-mgs --mdt setup-mds:/fake/path/1 --ost setup-oss0:/fake/path/3 --ost setup-oss1:/fake/path/4
  Then the filesystem count should be 1
  And the target count should be 4
  And the mgt count should be 1
  And the ost count should be 2
