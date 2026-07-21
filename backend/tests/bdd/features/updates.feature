Feature: In-app updates
  As a user
  I want the app to check for newer releases
  So that I can install updates with one click

  Scenario: A newer release is available
    Given the running version is "0.7.0"
    And the latest published release is "0.8.0"
    When I check for updates
    Then an update should be reported as available
    And the installer asset URL should point to a GitHub host

  Scenario: The running version is current
    Given the running version is "0.7.0"
    And the latest published release is "0.7.0"
    When I check for updates
    Then no update should be reported

  Scenario: The update server is unreachable
    Given the running version is "0.7.0"
    And the update server is unreachable
    When I check for updates
    Then the check should fail with a network error
