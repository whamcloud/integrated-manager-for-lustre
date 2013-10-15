Feature: Manage Lustre targets with Chroma
  In order to manage targets in my Lustre filesystems
  As a Chroma administrator who likes using the CLI
  I want to type stuff in a shell to manage targets

Background: Set up the test environment
  Given the "exploration" data is loaded

Scenario: Stop an OST using target-stop
  Given the filesystem state on firstfs should be available
  And the target state on firstfs-OST0000 should be mounted
  When I run chroma target-stop firstfs-OST0000
  Then I should be prompted to proceed
  Then the target state on firstfs-OST0000 should be unmounted
  And the filesystem state on firstfs should be unavailable

Scenario: Start an OST using ost-start
  Given the target state on firstfs-OST0000 should be unmounted
  When I run chroma ost-start firstfs-OST0000
  Then the target state on firstfs-OST0000 should be mounted
  And the filesystem state on firstfs should be available

Scenario: Stop a MGT using mgt-stop
  Given the target state on MGS should be mounted
  When I run chroma mgt-stop MGS
  Then I should be prompted to proceed
  Then the target state on MGS should be unmounted

Scenario: Start a MGT using target-start
  Given the target state on MGS should be unmounted
  When I run chroma target-start MGS
  Then the target state on MGS should be mounted

Scenario: Remove an OST
  Given the ost count should be 24
  When I run chroma ost-remove secondfs-OST0000
  Then I should be prompted to proceed
  Then the ost count should be 23
  And the filesystem state on secondfs should be available

Scenario: Add an OST
  Given the ost count should be 23
  When I run chroma ost-add --reformat --filesystem secondfs secondfs-oss0:/dev/disk/by-id/scsi-1IET_000c0001
  Then the ost count should be 24
  And the target state on secondfs-OST0004 should be mounted

Scenario: Force a target failover
  Given the target active_host_name on MGS should be the same as primary_server_name
  When I run chroma target-failover MGS
  Then I should be prompted to proceed
  Then the target active_host_name on MGS should be the same as failover_server_name
  And the target state on MGS should be mounted

Scenario: Force a target failback
  Given the target active_host_name on MGS should be the same as failover_server_name
  When I run chroma target-failback MGS
  Then I should be prompted to proceed
  Then the target active_host_name on MGS should be the same as primary_server_name
  And the target state on MGS should be mounted
