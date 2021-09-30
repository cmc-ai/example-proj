# OS Envs: The 3 db envs
# Layers : true
# Permissions: rds, triggered by s3,

import boto3

from constants import DBDebtStatus, DBBorrowerChannelType
from helper_functions import get_or_create_pg_connection

s3_client = boto3.client('s3')
rds_client = boto3.client('rds')
pg_conn = None

S3_BUCKET_REGION = 'ca-central-1'


def lambda_handler(event, context):
    print(event)

    # extract meaningful fields
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']  # debts/1/dt.json
        print(f'Processing {bucket}/{key}')

        try:
            debts_folder, client_id, file_name = key.split('/')
            client_id = int(client_id)
            if debts_folder != 'debts':
                print('Pattern debts/{client_id}/{datetime}.csv  is not recognized')
                return
        except:
            print('Pattern debts/{client_id}/{datetime}.csv  is not recognized')
            return

        conn = get_or_create_pg_connection(pg_conn, rds_client)

        # create temp table
        temp_table = f'DebtBorrower_{client_id}_{file_name.split(".")[0]}'
        bucket_key = f'{bucket}/{key}'
        query = f"""
            CREATE TABLE IF NOT EXISTS {temp_table} (
            clientPortfolioId   int,
            originalBalance     DECIMAL(12,2) NOT NULL,
            outstandingBalance  DECIMAL(12,2) NOT NULL,
            totalPayment        DECIMAL(12,2),
            discount            DECIMAL(12,2),
            description         TEXT,
        
            firstName   char(50) NOT NULL,
            lastName    char(50) NOT NULL,
            phoneNum    char(20),
            email       char(50),
            timezone    char(50),
            country     char(10)
        )
        """
        print(f'QUERY: {query}')
        conn.run(query)
        conn.commit()

        try:
            # load s3 file into DB
            query = f"""
                SELECT aws_s3.table_import_from_s3(
                    '{temp_table}',
                    '',
                    '(format csv)',
                    '{bucket}',
                    '{key}',
                    '{S3_BUCKET_REGION}'
                )
            """
            print(f'QUERY: {query}')
            conn.run(query)
            conn.commit()

            # insert into Debt, Borrower
            query = f"""
                with d as (insert into Debt (
                clientId, clientPortfolioId, originalBalance, outstandingBalance,
                totalPayment, discount, description, status,
                createDate, lastUpdateDate, s3SourceFile)
                select {client_id}, clientPortfolioId, originalBalance, outstandingBalance,
                        totalPayment, discount, description, '{DBDebtStatus.waiting_journey_assignment.value}',
                        current_timestamp, current_timestamp, '{bucket_key}'
                from {temp_table}
                returning id),
                b as (insert into Borrower (
                    debtId, firstName, lastName, isPrimary, channelType, phoneNum, email, timezone, country,
                    createDate, lastUpdateDate, s3SourceFile)
                select db_d.id, db_d.firstName, db_d.lastName, True, '{DBBorrowerChannelType.SMS.value}', 
                db_d.phoneNum, db_d.email, db_d.timezone, db_d.country, 
                current_timestamp, current_timestamp, '{bucket_key}'
                from (  select d_rn.id,
                        db_rn.firstName, db_rn.lastName, db_rn.phoneNum, db_rn.email, db_rn.timezone, db_rn.country
                        from
                        (SELECT row_number() OVER (), * FROM {temp_table}) db_rn
                        join
                        (SELECT row_number() OVER (), * FROM d) d_rn
                        using (row_number)
                    ) db_d
                )
                select count(1) from d;
            """
            print(f'QUERY: {query}')
            conn.run(query)
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'Failed to load data from {bucket_key}')
            print(e)

        print(f"Drop table {temp_table}")
        # In all cases delete temp table if exists
        query = f"DROP TABLE IF EXISTS {temp_table};"
        print(f'QUERY: {query}')
        conn.run(query)
        conn.commit()

    return
