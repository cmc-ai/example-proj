-- Client
INSERT INTO Client
	(username, password, token, firstName, lastName, phoneNum, email, organization, createDate, lastUpdateDate)
VALUES
	('client1', 'p@ssword', 'asdfasdf', 'Name', 'Surname', '88005553535', 'manager@bank.com', 'TheBank', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


INSERT INTO ClientPortfolio (clientId, portfolioName, createDate, lastUpdateDate )
VALUES (1, 'first_portfolio', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO ClientConfiguration (clientPortfolioId, linkExpMinutes, gapBetweenJourneysDays, createDate, lastUpdateDate)
VALUES (1, 60, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Debt
INSERT INTO Debt
	(clientId, clientPortfolioId, originalBalance, outstandingBalance, totalPayment, discount, createDate, lastUpdateDate)
VALUES
	(1, 1, 150.0, 150.0, 0.0, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
	(1, 1, 150.0, 150.0, 0.0, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
	(1, 1, 150.0, 150.0, 0.0, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO DebtPayment
(debtId, paymentDateTimeUTC, amount, paymentStatus, fundingAccSummary, paymentProcessor, debtLevel, paymentSource, accountType, createDate, lastUpdateDate)
values (1, CURRENT_TIMESTAMP, 40.5, 'paymentStatus', 'fundingAccSummary', 'paymentProcessor', 4, 'paymentSource', 'accountType', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)

-- Borrower
INSERT INTO Borrower
    (debtId, firstName, lastName, isPrimary, channelType, phoneNum, email,  createDate, lastUpdateDate)
VALUES
    (52, 'Wei', 'Luo', true, 'SMS', '+10000111156', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (53, 'Shiyi', 'Chen', true, 'SMS', '+10000111196', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (54, 'Haoyan', 'Zhai', true, 'SMS', '+10000111169', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


-- Journey Activity
INSERT INTO Journey (awsId, clientId,  createDate, lastUpdateDate)
VALUES ('', 1,  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO JourneyEntryActivity (journeyId, debtId, entryDateTimeUTC, createDate, lastUpdateDate)
VALUES (1, 52,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP),
(1, 53,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP),
(1, 54,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP,  CURRENT_TIMESTAMP);

--select column_name, data_type, character_maximum_length, column_default, is_nullable
--from INFORMATION_SCHEMA.COLUMNS where table_name = 'clientfundingaccount';

--select * from client;
--select * from clientfundingaccount;
