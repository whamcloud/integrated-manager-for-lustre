Feature: Manage Lustre targets with Chroma
  In order to manage targets in my Lustre filesystems
  As a Chroma administrator who likes using the CLI
  I want to type stuff in a shell to manage targets

Background: Set up the test environment
  Given the "exploration" data is loaded

Scenario: Add an MDT
  Given the mdt count should be 2
  When I run chroma mdt-add --reformat --filesystem secondfs secondfs-mds:/dev/disk/by-id/scsi-1IET_000b0002
  Then the mdt count should be 3
  And the target state on secondfs-MDT0001 should be mounted

Scenario: Check an MDT0 cannot be removed
  Given the mdt count should be 3
  And the following commands will fail
  When I run chroma mdt-remove secondfs-MDT0000
  Then the mdt count should be 3
  And the target state on secondfs-MDT0000 should be mounted

Scenario: Check an MDT1 cannot be removed
  Given the mdt count should be 3
  And the following commands will fail
  When I run chroma mdt-remove secondfs-MDT0001
  Then the mdt count should be 3
  And the target state on secondfs-MDT0001 should be mounted