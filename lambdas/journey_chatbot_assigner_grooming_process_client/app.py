import boto3
from contextlib import closing
# this dependencies are deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection
from constants import DBDebtStatus

rds_client = boto3.client('rds')
pg_conn = None


def create_db_connection():
    global pg_conn
    global rds_client
    return get_or_create_pg_connection(pg_conn, rds_client)


def lambda_handler(event, context):
    conn = create_db_connection()
    query = f"""
                SELECT DISTINCT clientid FROM Debt as d WHERE  d.status='{DBDebtStatus.waiting_journey_assignment.value}';
            """
    with closing(conn.cursor()) as cursor:
        rows = cursor.execute(query).fetchall()
        if rows:
            return {
                'statusCode': 200,
                'body': rows[0]
            }


if __name__ == "__main__":
    print(lambda_handler({}, None))
# PYTHONPATH=../common/python DBEndPoint="chatbot-dev-aurora-db-postgres-1.cd4lkfqaythe.ca-central-1.rds.amazonaws.com"  DatabaseName="symphony" DBUserName="superuser" python3 app.py


{"Id":8,"ChannelType":"SMS","Address":"+16502546320","Location":{"Country":"US"}, "User":{"UserId":1, "UserAttributes":  {"FirstName":  ["Stan"], "LastName": ["Nikitin"]}}}