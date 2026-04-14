Feature: Proposal review workflow
  As a user
  I want to review and approve classification proposals
  So that my documents are filed correctly

  Scenario: Approve a proposal
    Given there is a pending proposal
    When I approve the proposal
    Then the proposal status should be "approved"

  Scenario: Reject a proposal
    Given there is a pending proposal
    When I reject the proposal
    Then the proposal status should be "rejected"

  Scenario: Correct a proposal
    Given there is a pending proposal
    When I correct the proposal with name "fixed.pdf" and folder "Correct/Folder"
    Then the proposal status should be "corrected"
    And the proposed name should be "fixed.pdf"
    And the proposed folder should be "Correct/Folder"

  Scenario: Execute approved proposals
    Given there are 2 approved proposals with existing source files
    When I execute the approved proposals
    Then each file should be moved to its target location
    And the moves should be logged in the audit trail
