-- insert this after the test_data

-- Debts
INSERT INTO Debt
	(clientId, clientPortfolioId, originalBalance, outstandingBalance, totalPayment, discount, createDate, lastUpdateDate)
VALUES
	(1, 1, 16.00,   9.00,   5.00,   1.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 3
	(1, 1, 160.00,  40.00,  120.00, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 4
	(1, 1, 160.00,  40.00,  120.00, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 5
	(1, 1, 160.00,  40.00,  120.00, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 6
	(1, 1, 1600.00,  400.00,  1200.00, 100.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 7
	(1, 1, 160.00,  40.00,  120.00, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 8
	(1, 1, 160.00,  40.00,  120.00, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 9
	(1, 1, 0.00,    0.00,   0.00,   0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 10
	(1, 1, 110.00,  0.00,   110.00, 0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 11
	(1, 1, 110.00,  110.00,  0.00,  10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 12
	(1, 1, 0.00,    0.00,   0.00,   0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),  -- 13
	(1, 1, 0.00,    0.00,   0.00,   0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);  -- 14

-- Borrowers
INSERT INTO Borrower
    (debtId, firstName, lastName, isPrimary, channelType, phoneNum, email, createDate, lastUpdateDate)
VALUES
    (3, 'Stan', 'Nikitin', true, 'SMS',         '88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 15
    (4, 'Max', 'Tereshin', true, 'SMS',         '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (5, 'Alex', 'Zavialov', true, 'SMS',        '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (6, 'Wei', 'Luo', true, 'SMS',              '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (7, 'Vladimir', 'Putin', true, 'SMS',       '+1', '',            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (8, 'Azat', 'Safin', true, 'SMS',           '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (9, 'Grigorii', 'Vodolagin', true, 'SMS',   '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (10, 'Shiyi', 'Chen', true, 'SMS',          '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (11, 'Haoyan', 'Zhai ', true, 'SMS',        '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (12, 'Ilnur', 'Yakupov', true, 'SMS',       '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (13, 'Azat', 'Mutigullin', true, 'SMS',     '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (14, 'Stanislav', 'Nikitin', true, 'SMS',   '+88005553535', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);  -- 26

-- Journey
INSERT INTO Journey
    (awsId, clientId, createDate, lastUpdateDate)
VALUES
    ('asdasdasdas-4', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP); -- 1

INSERT INTO JourneyDebtStatusDefinition
    (statusName, createDate, lastUpdateDate)
VALUES
    ('status', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP); -- 7

INSERT INTO JourneyEntryActivity
    (journeyId, debtId, entryDateTimeUTC, createDate, lastUpdateDate)
VALUES
    (1, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 2
    (1, 4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 3
    (1, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 4
    (1, 6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 5
    (1, 7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 6
    (1, 8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 7
    (1, 9, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 8
    (1, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 9
    (1, 11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 10
    (1, 12, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 11
    (1, 13, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), -- 12
    (1, 14, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP); -- 13


INSERT INTO JourneyDebtStatus
    (journeyEntryActivityId, journeyDebtStatusDefinitionId, statusValue, createDate, lastUpdateDate)
VALUES
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'pre-working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'post-working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'complete', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'inactive', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 7, 'working', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


INSERT INTO BorrowerFundingAccount
    (borrowerId, accountType, summary, cardNumber, cardHolder, cvc, expMonYear, clientIdExternal, paymentProcessor, paymentProcessorUserId, token, createDate, lastUpdateDate)
VALUES
    (1, 'cc', 'idk some summary', 8888333366665555, 'Stanislav Nikitin', 123, '03/22', 124132, 'Swerve', '1234', 'dasfdasd3fDF', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (1, 'cc', 'another summary', 5230297993477937, 'Firstname Lastname', 125, '03/21', 124132, 'Swerve', '52353', 'dasadfdsfdasd3fDF', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)