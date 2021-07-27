--- Clients

CREATE TABLE IF NOT EXISTS Client (
    id          int NOT NULL AUTO_INCREMENT,
    username    char(50) NOT NULL,
    password    char(50) NOT NULL,
    token       char(200),  -- ???
    firstName   char(50),
    lastName    char(50),
    phoneNum    char(20),
    email       char(50),
    organization        char(50),
    createDate  DATETIME,
    lastUpdateDate DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ClientFundingAccount (
    id              int NOT NULL AUTO_INCREMENT,
    clientId        int NOT NULL,
    accountType     char(20) NOT NULL,
    summary         char(50) NOT NULL,
    paymentProcessor    char(200),
    token           char(200),
    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS APICall (
    id              int NOT NULL AUTO_INCREMENT,  -- int? bigint?
    clientId        int NOT NULL,
    callDateTime    DATETIME NOT NULL,
    method          char(10),
    url             char(100),
    payload         char(500),
    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JorneyConfiguration (
    id              int NOT NULL AUTO_INCREMENT,
    clientId        int NOT NULL,
    linkExpMinutes  int,
    gapBetweenJourneysDays  int,
    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ChatbotConfiguration (
    id              int NOT NULL AUTO_INCREMENT,
    clientId        int NOT NULL,
    -- config fields ?

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

--- Borrowers

CREATE TABLE IF NOT EXISTS Debt (
    id          int NOT NULL AUTO_INCREMENT,
    clientId    int NOT NULL,
    debtTypeId  int,
    originalBalance     DECIMAL(12,2) NOT NULL,
    outstandingBalance  DECIMAL(12,2) NOT NULL,
    totalPayment        DECIMAL(12,2),
    discount            DECIMAL(12,2),

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS Borrower (
    id          int NOT NULL AUTO_INCREMENT,
    debtId      int NOT NULL,
    firstName   char(50) NOT NULL,
    lastName    char(50) NOT NULL,
    isPrimary   boolean NOT NULL,
    channelType char(50) NOT NULL,
    phoneNum    char(20),
    email       char(50),

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS BorrowerFundingAccount (
    id              int NOT NULL AUTO_INCREMENT,
    borrowerId      int NOT NULL,
    accountType char(20) NOT NULL,
    summary     char(50) NOT NULL,
    debtLevel   int,
    paymentProcessor char(200),
    token       char(200),
    createDate  DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS DebtPayment (  -- Debt Activity
    id                  int NOT NULL AUTO_INCREMENT,
    debtId              int NOT NULL,
    paymentDateTime     DATETIME NOT NULL,
    amount              DECIMAL(12,2) NOT NULL,
    paymentStatus       char(20) NOT NULL,
    fundingAccSummary   char(50) NOT NULL,
    paymentProcessor    char(200),
    debtLevel           int,
    paymentSource       char(200),
    vendorTransId       char(200),
    statusReason        TEXT,
    accountType         CHAR(50) NOT NULL,
    createDate          DATETIME,
    lastUpdateDate      DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS DebtPaymentLink (
    id                  int NOT NULL AUTO_INCREMENT,
    debtId              int NOT NULL,
    url                 char(100),
    expirationDateTime  DATETIME,

    createDate          DATETIME,
    lastUpdateDate      DATETIME,

    PRIMARY KEY (id)
);

-- Jorney & ChatBot

CREATE TABLE IF NOT EXISTS Journey (
    id          int NOT NULL AUTO_INCREMENT,
    awsId       CHAR(50),
    jorneyConfigurationId int,

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS Chatbot (                        -- where to use ?
    id                      int NOT NULL AUTO_INCREMENT,
    awsId                   CHAR(50),
    chatbotConfigurationId  int,

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyEntryActivity (
    id          int NOT NULL AUTO_INCREMENT,
    journeyId   int NOT NULL,
    debtId      int NOT NULL,
    entryDateTime   DATETIME NOT NULL,
    exitDateTime    DATETIME,
    isResponded     boolean,    -- JourneyDebtStatus
    hasPaid         boolean,

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS JourneyExeActivity (
    id          int NOT NULL AUTO_INCREMENT,
    journeyId   int NOT NULL,
    debtId      int NOT NULL,
    journeyEntryActivityId      int NOT NULL,
    entryDateTime   DATETIME NOT NULL,
    chatSessionID   CHAR(200),  -- ???

    createDate      DATETIME,
    lastUpdateDate  DATETIME,

    PRIMARY KEY (id)
);

-- Add Foreign key

ALTER TABLE ClientFundingAccount
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE APICall
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE JorneyConfiguration
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE ChatbotConfiguration
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE;

ALTER TABLE Debt
ADD FOREIGN KEY (clientId) REFERENCES Client(id) ON DELETE CASCADE,
ADD FOREIGN KEY (debtTypeId) REFERENCES DebtType(id) ON DELETE CASCADE;

ALTER TABLE Borrower
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE BorrowerFundingAccount
ADD FOREIGN KEY (borrowerId) REFERENCES Borrower(id) ON DELETE CASCADE;

ALTER TABLE DebtPaymentLink
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE DebtPayment
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE;

ALTER TABLE Journey
ADD FOREIGN KEY (jorneyConfigurationId) REFERENCES JorneyConfiguration(id) ON DELETE CASCADE;

ALTER TABLE Chatbot
ADD FOREIGN KEY (chatbotConfigurationId) REFERENCES ChatbotConfiguration(id) ON DELETE CASCADE;

ALTER TABLE JourneyEntryActivity
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyId) REFERENCES Journey(id) ON DELETE CASCADE;

ALTER TABLE JourneyExeActivity
ADD FOREIGN KEY (debtId) REFERENCES Debt(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyId) REFERENCES Journey(id) ON DELETE CASCADE,
ADD FOREIGN KEY (journeyEntryActivityId) REFERENCES JourneyEntryActivity(id) ON DELETE CASCADE;

