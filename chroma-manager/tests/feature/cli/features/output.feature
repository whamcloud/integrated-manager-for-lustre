Feature: Choose CLI output style
  In order to write scripts or use the CLI without bleeding eyes
  As a Chroma admin or user
  I want to be able to choose the CLI output format

Background: Load minimal data for output testing
  Given the "output-testing" data is loaded

Scenario: Default output for humans
  When I run chroma server-list
  Then I should see output containing "| id |"

Scenario: Comma-separated output
  When I run chroma --output csv server-list
  Then I should see output containing ","

Scenario: Tab-separated output
  When I run chroma --output tsv server-list
  Then I should see output containing "	"

Scenario: JSON output
  When I run chroma --output json server-list
  Then I should see output containing "[{"
  And I should see output containing ""address": ""
  And I should see output containing "}]"

Scenario: YAML output
  When I run chroma --output yaml server-list
  Then I should see output containing "- address: "
