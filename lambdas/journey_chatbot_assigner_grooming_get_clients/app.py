# ENV VARIABLE: DBEndPoint="chatbot-dev-aurora-db-postgres-1.cd4lkfqaythe.ca-central-1.rds.amazonaws.com"
# ENV VARIABLE: DatabaseName="symphony"
# ENV VARIABLE: DatabaseName="symphony" DBUserName="superuser"
# ENV VARIABLE: DBUserName="superuser"

import boto3
import pg8000
from contextlib import closing

# this dependencies are deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection
from constants import DBDebtStatus

rds_client = boto3.client('rds')
pg_conn = None


def create_db_connection() -> pg8000.Connection:
    global pg_conn
    global rds_client
    return get_or_create_pg_connection(pg_conn, rds_client)


def lambda_handler(event, context):
    print(f"Received event: {event}")
    params = event['Input']
    conn = create_db_connection()
    query = f"""
                SELECT DISTINCT clientid FROM Debt as d WHERE  d.status='{DBDebtStatus.waiting_journey_assignment.value}';
            """
    with closing(conn.cursor()) as cursor:
        rows = cursor.execute(query).fetchall()
        if rows:
            return {
                'statusCode': 200,
                'items': [{'client_id': i[0], 'pinpoint_project_id': params['pinpoint_project_id']} for i in rows]
            }

#
# if __name__ == "__main__":
#     print(lambda_handler({"pinpoint_project_id": '34e7ff51c4824c079b9ab87a6a530c2b'}, None))
