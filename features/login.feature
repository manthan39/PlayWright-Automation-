Feature: login action

    As a user
    I want login into application

    Scenario: Login with valid credentails
        Given I visit a login page
        When Enter Username
        When Enter password
        When Click on the Login Button
        Then Verify the logo