-- Client
INSERT INTO Client
	(username, password, token, firstName, lastName, phoneNum, email, organization, createDate, lastUpdateDate)
VALUES
	('client1', 'p@ssword', 'asdfasdf', 'Name', 'Surname', '88005553535', 'manager@bank.com', 'TheBank', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

--INSERT INTO ClientFundingAccount
--    (clientId, accountType, summary, paymentProcessor, token, createDate, lastUpdateDate)
--VALUES
--    (1, 'loan', 'summary', 'gggg', 'asdfasdf', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO ClientPortfolio (clientId, portfolioName, createDate, lastUpdateDate )
VALUES (1, 'first_portfolio', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO ClientConfiguration (clientPortfolioId, linkExpMinutes, gapBetweenJourneysDays, createDate, lastUpdateDate)
VALUES (1, 60, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Debt
INSERT INTO Debt
	(clientId, clientPortfolioId, originalBalance, outstandingBalance, totalPayment, discount, createDate, lastUpdateDate)
VALUES
	(1, 1, 16.38, 4.50, 10.44, 0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
	(1, 1, 160.38, 40.50, 100.44, 10.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Borrower
INSERT INTO Borrower
    (debtId, firstName, lastName, isPrimary, channelType, phoneNum, email,  createDate, lastUpdateDate)
VALUES
    (1, 'Stan', 'Nikitin', true, 'SMS', '', '',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

