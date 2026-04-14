Feature: Audit trail
  As a user
  I want all actions to be logged
  So that I can trace what happened to my documents

  Scenario: Pipeline run is logged
    Given I run a pipeline with files
    When I query the audit log for action "pipeline_started"
    Then I should find at least 1 entry

  Scenario: File moves are logged
    Given a file has been moved by the FileManager
    When I query the audit log for action "file_moved"
    Then I should find the source and target paths in the entry

  Scenario: Filter audit log by action
    Given multiple audit entries exist
    When I query the audit log filtered by action "classified"
    Then only entries with action "classified" should be returned

  Scenario: Filter audit log with limit
    Given 10 audit entries exist
    When I query the audit log with limit 5
    Then I should receive at most 5 entries
