Feature: Document processing pipeline
  As a user
  I want to process scanned documents through the pipeline
  So that they are classified and ready for filing

  Scenario: Run pipeline with files in inbox
    Given the inbox contains 2 PDF files
    When I run the pipeline
    Then I should receive 2 proposals
    And each proposal should have status "pending"
    And each proposal should have a proposed name
    And each proposal should have a proposed folder

  Scenario: Run pipeline with empty inbox
    Given the inbox is empty
    When I run the pipeline
    Then I should receive 0 proposals

  Scenario: Run pipeline with mixed file types
    Given the inbox contains 1 PDF file and 1 DOCX file
    When I run the pipeline
    Then I should receive 1 proposals
    And the unsupported file should be ignored
