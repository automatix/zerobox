Feature: Rule management and learning
  As a user
  I want to manage rule profiles
  So that classification improves over time

  Scenario: Create a rule profile
    Given no profiles exist
    When I create a profile "invoices" with name "Invoice Rules"
    Then the profile should be saved
    And listing profiles should return 1 profile

  Scenario: Add a rule to a profile
    Given a profile "invoices" exists
    When I add a rule with patterns ["Rechnung", "Stadtwerke"]
    Then the profile should contain 1 rule
    And the rule should have the correct patterns

  Scenario: Match rules against document text
    Given a profile with a rule matching "Rechnung" and "Stadtwerke"
    When I match rules against text containing "Rechnung von Stadtwerke GmbH"
    Then the rule should match

  Scenario: No match for unrelated text
    Given a profile with a rule matching "Rechnung" and "Stadtwerke"
    When I match rules against text containing "Mietvertrag Wohnung"
    Then no rules should match

  Scenario: Delete a rule from a profile
    Given a profile "invoices" with 2 rules
    When I delete the first rule
    Then the profile should contain 1 rule
