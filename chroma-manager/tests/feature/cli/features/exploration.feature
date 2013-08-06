Feature: Explore a Chroma installation
  In order to discover or examine aspects of my Chroma installation
  As a Chroma administrator
  I want to use the chroma CLI to explore my installation

Background: Set up the feature configuration
  Given the "exploration" data is loaded

Scenario: List all servers
  When I run chroma server-list
  Then I should see output containing "exploration-mgs"
  And I should see output containing "firstfs-mds"
  And I should see output containing "firstfs-oss0"
  And I should see output containing "secondfs-mds"
  And I should see output containing "secondfs-oss1"

Scenario: List all servers for a given filesystem
  When I run chroma filesystem firstfs server-list
  Then I should see output containing "exploration-mgs"
  And I should see output containing "firstfs-mds"
  And I should see output containing "firstfs-oss0"
  And I should see output containing "firstfs-oss1"
  But I should not see output containing "secondfs"

Scenario: View a specific server
  When I run chroma server-show firstfs-oss0
  Then I should see output containing "firstfs-oss0.lab.whamcloud.com"

Scenario: List all filesystems
  When I run chroma filesystem-list
  Then I should see output containing "firstfs"
  And I should see output containing "secondfs"

Scenario: View a specific filesystem
  When I run chroma filesystem-show firstfs
  Then I should see output containing "firstfs"

Scenario: List all MGTs
  When I run chroma mgt-list
  Then I should see output containing "MGS"

Scenario: List MGT for a given filesystem
  When I run chroma filesystem firstfs mgt-list
  Then I should see output containing "MGS"

Scenario: View a specific MGT
  When I run chroma mgt-show MGS
  Then I should see output containing "exploration-mgs"

Scenario: List all MDTs
  When I run chroma mdt-list
  Then I should see output containing "firstfs-MDT0000"
  And I should see output containing "secondfs-MDT0000"

Scenario: List MDT for a given filesystem
  When I run chroma filesystem secondfs mdt-list
  Then I should see output containing "secondfs-MDT0000"
  But I should not see output containing "firstfs-MDT0000"

Scenario: View a specific MDT
  When I run chroma mdt-show firstfs-MDT0000
  Then I should see output containing "firstfs-mds"

Scenario: List all OSTs
  When I run chroma ost-list
  Then I should see output containing "firstfs-OST0000"
  And I should see output containing "firstfs-OST0007"
  And I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0003"

Scenario: List all OSTs for a given filesystem
  When I run chroma filesystem secondfs ost-list
  Then I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0001"
  And I should see output containing "secondfs-OST0002"
  And I should see output containing "secondfs-OST0003"
  But I should not see output containing "firstfs"

Scenario: List all OSTs for a given server
  When I run chroma server secondfs-oss0 ost-list
  Then I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0001"
  And I should see output containing "secondfs-OST0002"
  And I should see output containing "secondfs-OST0003"

Scenario: List all OSTs for a given server, restricting to primaries only
  When I run chroma server secondfs-oss0 ost-list --primary
  Then I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0002"
  But I should not see output containing "secondfs-OST0001"

Scenario: View a specific OST
  When I run chroma ost-show firstfs-OST0002
  Then I should see output containing "scsi-1IET_00030001"

Scenario: List all targets
  When I run chroma target-list
  Then I should see output containing "MGS"
  And I should see output containing "firstfs-MDT0000"
  And I should see output containing "secondfs-MDT0000"
  And I should see output containing "firstfs-OST0000"
  And I should see output containing "firstfs-OST0007"
  And I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0003"

Scenario: List all targets for a given filesystem
  When I run chroma filesystem secondfs target-list
  Then I should see output containing "secondfs-MDT0000"
  And I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0001"
  And I should see output containing "secondfs-OST0002"
  And I should see output containing "secondfs-OST0003"
  But I should not see output containing "firstfs-MDT0000"

Scenario: List all targets for a given server
  When I run chroma server secondfs-oss1 target-list
  Then I should see output containing "secondfs-MDT0000"
  And I should see output containing "secondfs-OST0000"
  And I should see output containing "secondfs-OST0003"

Scenario: List all targets for a given server, restricting to primaries only
  When I run chroma server firstfs-oss0 target-list --primary
  Then I should see output containing "firstfs-OST0000"

Scenario: View a specific target
  When I run chroma target-show secondfs-MDT0000
  Then I should see output containing "scsi-1IET_000b0001"

Scenario: List usable volumes
  When I run chroma volume list
  Then I should see output containing "Found 0 results"
  And there should be 0 lines of output

Scenario: List all volumes
  When I run chroma volume list --all
  Then I should see output containing "scsi-1IET_00010001"
  And I should see output containing "scsi-1IET_000f0001"
  And I should see output containing "firstfs-mds.lab.whamcloud.com:/dev/disk/by-id/scsi-1IET_00020001"
  And I should see output containing "firstfs-oss0.lab.whamcloud.com:/dev/disk/by-id/scsi-1IET_00020001"
  And there should be 27 lines of output

Scenario: List all volumes for a given filesystem
  When I run chroma filesystem secondfs volume-list
  Then I should see output containing "scsi-1IET_00010001"
  And I should see output containing "scsi-1IET_000b0001"
  And I should see output containing "scsi-1IET_000f0001"
  But I should not see output containing "scsi-1IET_00050001"

Scenario: List all volumes for a given server
  When I run chroma server secondfs-oss1 volume-list
  Then I should see output containing "scsi-1IET_000b0001"
  And I should see output containing "scsi-1IET_000f0001"
  But I should not see output containing "scsi-1IET_00050001"

Scenario: List all volumes for a given server, restricting to primaries only
  When I run chroma server firstfs-oss0 volume-list --primary
  Then I should see output containing "scsi-1IET_00050001"
  And I should see output containing "scsi-1IET_00030001"
  And I should see output containing "scsi-1IET_00040001"
  And I should see output containing "scsi-1IET_00060001"
  But I should not see output containing "scsi-1IET_00080001"

Scenario: View a specific volume
  When I run chroma volume-show scsi-1IET_00050001
  Then I should see output containing "firstfs-oss0"
  And I should see output containing "firstfs-oss1"

Scenario: List all MGSes
  When I run chroma mgs-list
  Then I should see output containing "exploration-mgs"

Scenario: List MGS for a given filesystem
  When I run chroma filesystem firstfs mgs-list
  Then I should see output containing "exploration-mgs"

Scenario: View a specific MGS
  When I run chroma mgs-show exploration-mgs
  Then I should see output containing "exploration-mgs.lab.whamcloud.com"

Scenario: List all OSSes
  When I run chroma oss-list
  Then I should see output containing "firstfs-oss0"
  And I should see output containing "secondfs-oss1"

Scenario: List all OSSes for a given filesystem
  When I run chroma filesystem firstfs oss-list
  Then I should see output containing "firstfs-oss0"
  And I should see output containing "firstfs-oss1"
  But I should not see output containing "secondfs"

Scenario: List all MDSes
  When I run chroma mds-list
  Then I should see output containing "firstfs-mds"
  And I should see output containing "secondfs-mds"

Scenario: List all MDSes for a given filesystem
  When I run chroma filesystem secondfs mds-list
  Then I should see output containing "secondfs-mds"
  But I should not see output containing "firstfs-mds"

Scenario: View client mount information for a given filesystem
  When I run chroma filesystem-mountspec firstfs
  Then I should see output containing "192.168.0.1@tcp0:192.168.0.2@tcp0:/firstfs"
