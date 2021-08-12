import os

import pg8000


def get_or_create_pg_connection(pg_conn, rds_client):

    if pg_conn:
        return pg_conn

    try:
        print("Connecting to database")

        DBEndPoint = os.environ.get("DBEndPoint")
        DatabaseName = os.environ.get("DatabaseName")
        DBUserName = os.environ.get("DBUserName")
        password = rds_client.generate_db_auth_token(DBHostname=DBEndPoint, Port=5432, DBUsername=DBUserName)

        # Establishes the connection with the server using the token generated as password
        pg_conn = pg8000.connect(
            host=DBEndPoint,
            user=DBUserName,
            database=DatabaseName,
            password=password,
            ssl_context=True
        )

        print("Connected to database")
        return pg_conn

    except Exception as e:
        print("While connecting failed due to :{0}".format(str(e)))
        return None