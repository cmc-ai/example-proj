import boto3
from contextlib import closing
# this dependencies are deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection

rds_client = boto3.client('rds')
pg_conn = None


def create_db_connection():
    global pg_conn
    global rds_client
    return get_or_create_pg_connection(pg_conn, rds_client)


def lambda_handler(event, context):
    conn = create_db_connection()
    query = f"""
                SELECT DISTINCT clientid FROM Debt as d WHERE  d.status='WaitingForJourney';
            """
    with closing(conn.cursor()) as cursor:
        rows = cursor.execute(query).fetchall()
        clients_ids = rows[0]
        return {
            'statusCode': 200,
            'body': clients_ids
        }


if __name__ == "__main__":
    print(lambda_handler({}, None))
# PYTHONPATH=../common/python DBEndPoint="chatbot-dev-aurora-db-postgres-1.cd4lkfqaythe.ca-central-1.rds.amazonaws.com"  DatabaseName="symphony" DBUserName="superuser" python3 app.py
