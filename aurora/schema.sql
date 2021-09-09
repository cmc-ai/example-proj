-- Drops
DROP TABLE IF EXISTS Client CASCADE;
DROP TABLE IF EXISTS ClientFundingAccount CASCADE;
DROP TABLE IF EXISTS ClientPortfolio CASCADE;
DROP TABLE IF EXISTS ClientConfiguration CASCADE;
DROP TABLE IF EXISTS Debt CASCADE;
DROP TABLE IF EXISTS Borrower CASCADE;
DROP TABLE IF EXISTS BorrowerFundingAccount CASCADE;
DROP TABLE IF EXISTS DebtPayment CASCADE;
DROP TABLE IF EXISTS DebtPaymentLink CASCADE;
DROP TABLE IF EXISTS Journey CASCADE;
DROP TABLE IF EXISTS Chatbot CASCADE;
DROP TABLE IF EXISTS JourneyEntryActivity CASCADE;
DROP TABLE IF EXISTS JourneyDebtStatusDefinition CASCADE;
DROP TABLE IF EXISTS JourneyDebtStatus CASCADE;
DROP TABLE IF EXISTS JourneyExeActivity CASCADE;

--- Clients
CREATE TABLE IF NOT EXISTS Client (
    id          SERIAL,
    username    char(50) NOT NULL,
    password    char(50),
    token       char(200),
    firstName   char(50),
    lastName    char(50),
    phoneNum    char(20),
    email       char(50),
    organization        char(50),

    createDate  timestamp,
    lastUpdateDate timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ClientFundingAccount (
    id              SERIAL,
    clientId        int NOT NULL,
    accountType     char(20),
    summary         char(50),
    paymentProcessor    char(200),
    token           char(200),
    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ClientPortfolio (
    id              SERIAL,
    clientId        int NOT NULL,
    portfolioName   char(50),
    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ClientConfiguration (
    id                      SERIAL,
    clientPortfolioId       int NOT NULL,
    linkExpMinutes          int,
    gapBetweenJourneysDays  int,
    createDate          timestamp,
    lastUpdateDate      timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS APICall (
    id              SERIAL,  -- int? bigint?
    clientId        int NOT NULL,
    callDateTimeUTC    timestamp NOT NULL,
    method          char(10),
    url             char(100),
    payload         char(500),
    createDate      timestamp, ---
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

--- Borrowers

CREATE TABLE IF NOT EXISTS Debt (
    id                  SERIAL,
    clientId            int NOT NULL,
    clientPortfolioId   int,
    originalBalance     DECIMAL(12,2) NOT NULL,
    outstandingBalance  DECIMAL(12,2) NOT NULL,
    totalPayment        DECIMAL(12,2),
    discount            DECIMAL(12,2),
    discountExpirationDateTimeUTC  timestamp,
    description         TEXT,

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS Borrower (
    id          SERIAL,
    debtId      int NOT NULL,
    firstName   char(50) NOT NULL,
    lastName    char(50) NOT NULL,
    isPrimary   boolean NOT NULL,
    channelType char(50) NOT NULL,
    phoneNum    char(20),
    email       char(50),
    timezone    char(50),
    country     char(10),

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS BorrowerFundingAccount (
    id              SERIAL,
    borrowerId      int NOT NULL,
    accountType char(20) NOT NULL,
    summary     char(50) NOT NULL,
    paymentProcessor char(200),
    token       char(200),
    createDate  timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS DebtPayment (  -- Debt Activity
    id                  SERIAL,
    debtId              int NOT NULL,
    paymentDateTimeUTC     timestamp NOT NULL,
    amount              DECIMAL(12,2) NOT NULL,
    paymentStatus       char(20) NOT NULL,
    fundingAccSummary   char(50) NOT NULL,
    paymentProcessor    char(200),
    debtLevel           int,
    paymentSource       char(200),
    vendorTransId       char(200),
    statusReason        TEXT,
    accountType         CHAR(50) NOT NULL,
    createDate          timestamp,
    lastUpdateDate      timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS DebtPaymentLink (   -- TODO Not needed
    id                  SERIAL,
    debtId              int NOT NULL,
    url                 char(100),
    expirationDateTimeUTC  timestamp,

    createDate          timestamp,
    lastUpdateDate      timestamp,

    PRIMARY KEY (id)
);

-- Journey & ChatBot

CREATE TABLE IF NOT EXISTS Journey ( -- TODO Not needed
    id          SERIAL,
    awsId       CHAR(50),
    clientId    int,

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS Chatbot (  -- TODO Not needed
    id              SERIAL,
    awsId           CHAR(50),
    clientId        int,

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyEntryActivity (
    id          SERIAL,
    journeyId   int NOT NULL,
    debtId      int NOT NULL,
    entryDateTimeUTC   timestamp NOT NULL,
    exitDateTimeUTC    timestamp,

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyDebtStatusDefinition (
    id          SERIAL,
    statusName  char(50),

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyDebtStatus (
    id          SERIAL,
    journeyEntryActivityId          int,
    journeyDebtStatusDefinitionId   int,
    statusValue                     char(50),

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyExeActivity (  -- TODO Not needed
    id          SERIAL,
    journeyId   int NOT NULL,
    debtId      int NOT NULL,
    journeyEntryActivityId      int NOT NULL,
    entryDateTimeUTC   timestamp NOT NULL,
    chatSessionID   CHAR(200),  -- ???

    createDate      timestamp,
    lastUpdateDate  timestamp,

    PRIMARY KEY (id)
);

-- Add Foreign key

ALTER TABLE ClientFundingAccount
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE ClientPortfolio
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE ClientConfiguration
ADD FOREIGN KEY (clientPortfolioId) REFERENCES ClientPortfolio(id) ON DELETE CASCADE;

ALTER TABLE APICall
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE Debt
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE,
ADD FOREIGN KEY (clientPortfolioId) REFERENCES ClientPortfolio(id) ON DELETE CASCADE;

ALTER TABLE Borrower
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE BorrowerFundingAccount
ADD FOREIGN KEY (borrowerId) REFERENCES Borrower(id) ON DELETE CASCADE;

ALTER TABLE DebtPaymentLink
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE DebtPayment
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE Journey
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE Chatbot
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE JourneyEntryActivity
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyId) REFERENCES Journey(id) ON DELETE CASCADE;

ALTER TABLE JourneyDebtStatus
ADD FOREIGN KEY (journeyEntryActivityId) REFERENCES JourneyEntryActivity(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyDebtStatusDefinitionId) REFERENCES JourneyDebtStatusDefinition(id) ON DELETE CASCADE;

ALTER TABLE JourneyExeActivity
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyId) REFERENCES Journey(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyEntryActivityId) REFERENCES JourneyEntryActivity(id) ON DELETE CASCADE;
