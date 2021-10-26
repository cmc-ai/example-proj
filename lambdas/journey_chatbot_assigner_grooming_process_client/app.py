# Manually created DynamoDB table: journey-process-status
# ENV VARIABLE: DYNAMODB_JOURNEY_PROCESS_STATUS_TABLE="journey-process-status"
# ENV VARIABLE: CLIENTS_S3_BUCKET_NAME="katabata-journey-chatbot-assigner-grooming"
# ENV VARIABLE: BASE_PATH="pinpoint_segments"
# ENV VARIABLE: PINPOINT_ROLE_ARN="arn:aws:iam::630063752049:role/PinpointSegmentImport"

import datetime
import json
import os
import time
from typing import List, Dict
import boto3
import pg8000
from contextlib import closing
from io import BytesIO
from botocore.exceptions import ClientError

# this dependencies are deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection
from constants import DBDebtStatus, JourneyProcessStatus
from dynamo_models import JourneyProcessStatusModel

s3_client = boto3.client('s3')
rds_client = boto3.client('rds')
pinpoint_client = boto3.client('pinpoint', region_name=os.getenv('AWS_REGION'))
pg_conn = None

# Use this set to reduce number of a DB calls
PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO = set()
PROCESSED_DEBTS_ID = set()
CURRENT_UTC_TS = int(datetime.datetime.utcnow().timestamp())

PINPOINT_JOURNEY_PREFIX = 'chatbot_journey_'


def create_db_connection() -> pg8000.Connection:
    global pg_conn
    global rds_client
    return get_or_create_pg_connection(pg_conn, rds_client)


def get_journey_process_statuses(client_id: int) -> Dict[int, JourneyProcessStatusModel]:
    journey_process_statuses = {}
    for item in JourneyProcessStatusModel.query(client_id):
        journey_process_statuses[item.portfolio_id] = item
    return journey_process_statuses


def set_journey_process_status(status: str, journey_process_status: JourneyProcessStatusModel) -> None:
    print(f"Set status: {status} for portfolio_id: {journey_process_status.portfolio_id}")
    journey_process_status.status = status
    journey_process_status.save()


def update_or_create_journey_process_status(client_id: int, portfolio_id: int, status: str,
                                            journey_process_statuses: Dict[int, JourneyProcessStatusModel]) -> None:
    print(f"Set journey process status: {status} for client_id: {client_id} and portfolio_id: {portfolio_id}")
    if portfolio_id in journey_process_statuses:
        if portfolio_id not in PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO:
            print(f"Update record with client_id: {client_id} and portfolio_id: {portfolio_id}")
            journey_process_statuses[portfolio_id].last_process_utc_ts = CURRENT_UTC_TS
            set_journey_process_status(status=status, journey_process_status=journey_process_statuses[portfolio_id])
            PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO.add(portfolio_id)

    else:
        print(f"Create new record with client_id: {portfolio_id} and debt_id: {portfolio_id}")
        journey_process_status = JourneyProcessStatusModel(client_id=client_id,
                                                           status=status,
                                                           portfolio_id=portfolio_id,
                                                           last_process_utc_ts=int(
                                                               datetime.datetime.utcnow().timestamp()))

        journey_process_status.save()
        journey_process_statuses[portfolio_id] = journey_process_status
        PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO.add(portfolio_id)


def is_record_need_to_process(record: Dict, journey_process_statuses: Dict[int, JourneyProcessStatusModel]) -> bool:
    # If we already added this portfolio_id to process list return True
    if record['portfolio_id'] in PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO:
        return True

    if (record['portfolio_id'] not in journey_process_statuses
            or journey_process_statuses[record['portfolio_id']].status == JourneyProcessStatus.failed.value
            or (CURRENT_UTC_TS - journey_process_statuses[
                record['portfolio_id']].last_process_utc_ts) / 60
            > record["updatesegmentinterval"]):
        return True
    return False


def get_borrower_items(client_id: int, journey_process_statuses: Dict[int, JourneyProcessStatusModel]) -> List[Dict]:
    conn = create_db_connection()
    query = f"""
                with a as (
                    select clientportfolioid,updateSegmentInterval, createdate from public.clientconfiguration WHERE clientportfolioid=90
                    order by createdate DESC limit 1
                )

                select d.id as debt_id, b.id, b.channeltype, b.phonenum, b.country, b.firstname, b.lastname, cp.id as portfolio_id, cc.updateSegmentInterval from public.Debt as d
                join public.ClientPortfolio cp on d.clientportfolioid = cp.id
                join a cc on cc.clientportfolioid = cp.id
                join public.Borrower as b on b.debtid = d.id
                WHERE d.clientid={client_id} and d.status='{DBDebtStatus.waiting_journey_assignment.value}';
            """
    with closing(conn.cursor()) as cursor:
        # Fetch SQL data
        rows = cursor.execute(query).fetchall()
        # Extract column names
        column_names = [column[0] for column in cursor.description]
        data = []
        if rows:
            for row in rows:
                # Build dict based on column names and values
                record = dict(zip(column_names, [v.rstrip() if isinstance(v, str) else v for v in row]))

                print("record", record)
                if is_record_need_to_process(record=record, journey_process_statuses=journey_process_statuses):
                    update_or_create_journey_process_status(client_id=client_id,
                                                            status=JourneyProcessStatus.in_progress.value,
                                                            portfolio_id=record['portfolio_id'],
                                                            journey_process_statuses=journey_process_statuses)
                    # Save processed debt id
                    PROCESSED_DEBTS_ID.add(record['debt_id'])

                    data.append(
                        {
                            "Id": int(time.time() * 1000),  # record['id'],
                            "ChannelType": record['channeltype'],
                            "Address": record['phonenum'],
                            "Location": {"Country": record['country']},
                            "User": {
                                "UserId": record['id'],
                                "UserAttributes": {
                                    "FirstName": [record['firstname']],
                                    "LastName": [record['lastname']]
                                }
                            }
                        }
                    )
        return data


def get_segment_from_s3(client_id: int) -> List[Dict]:
    s3_bucket = os.environ.get("CLIENTS_S3_BUCKET_NAME")
    s3_base_path = os.environ.get("BASE_PATH")
    try:
        obj = s3_client.get_object(Bucket=s3_bucket, Key=os.path.join(s3_base_path, f"client_id_{client_id}.json"))

        segments = []
        for item in obj['Body'].read().decode().split('\n'):
            if item:
                segments.append(json.loads(item))
        return segments
    except ClientError as e:
        if e.response['Error']['Code'] == "NoSuchKey":
            return []
        raise e


def save_borrower_items_to_s3(client_id: int, borrower_items: List[Dict]) -> str:
    s3_bucket = os.environ.get("CLIENTS_S3_BUCKET_NAME")
    s3_base_path = os.environ.get("BASE_PATH")

    already_saved_segments = get_segment_from_s3(client_id=client_id)
    borrower_items.extend(already_saved_segments)

    out = BytesIO()
    for item in borrower_items:
        out.write(f"{json.dumps(item)}\n".encode())

    out.seek(0)
    s3_client.put_object(
        Body=out,
        Bucket=s3_bucket,
        Key=os.path.join(s3_base_path, f"client_id_{client_id}.json"),
        ServerSideEncryption='aws:kms'
    )

    return "s3://{}".format(os.path.join(s3_bucket, s3_base_path, f"client_id_{client_id}.json"))


def get_or_create_journey_entry_activity(journey_id: str, debt_id: int) -> int:
    conn = create_db_connection()

    query = f"""
            SELECT id, journeyawsid, debtid FROM public.journeyentryactivity WHERE journeyawsid='{journey_id}' and debtid='{debt_id}';
        """
    with closing(conn.cursor()) as cursor:
        row = cursor.execute(query).fetchone()
        if row:
            journey_entry_activity_id = row[0]
            print(f"Found already created journey entry activity with id: {journey_entry_activity_id}")
            return journey_entry_activity_id

    query = f"""
            INSERT INTO public.journeyentryactivity(
            journeyawsid, debtid, entrydatetimeutc, createdate, lastupdatedate)
            VALUES ('{journey_id}', {debt_id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """
    print(f"Query: {query}")

    with closing(conn.cursor()) as cursor:
        row = cursor.execute(query).fetchone()
        conn.commit()
        journey_entry_activity_id = row[0]
        print(f"Created journey entry activity with id: {journey_entry_activity_id}")
        return journey_entry_activity_id


def create_pinpoint_journey(pinpoint_project_id: str, client_id: int, segment_id: str) -> Dict:
    print(
        f"Create journey for pinpoint project id: {pinpoint_project_id} client id: {client_id} segment id: {segment_id}")
    activity_id = int(time.time())
    ret = pinpoint_client.create_journey(
        ApplicationId=pinpoint_project_id,
        WriteJourneyRequest={
            'Activities': {
                f'{activity_id}': {
                    'CUSTOM': {
                        'DeliveryUri': os.getenv("PINPOINT_CUSTOM_LAMBDA_ARN"),
                        'EndpointTypes': ['CUSTOM', 'SMS']
                    }
                }
            },
            'Name': f'{PINPOINT_JOURNEY_PREFIX}{client_id}',
            'StartActivity': f'{activity_id}',
            'StartCondition': {
                'SegmentStartCondition': {
                    'SegmentId': segment_id
                }
            },
            'State': 'ACTIVE',
            'WaitForQuietTime': False,
            'RefreshOnSegmentUpdate': True,
            'RefreshFrequency': 'PT1H',
            'Schedule': {
                'EndTime': datetime.datetime.utcnow() + datetime.timedelta(days=500),
                'StartTime': datetime.datetime.utcnow() + datetime.timedelta(minutes=1),
                'Timezone': 'UTC'
            },
        }
    )
    print(f"Create journey response: {ret}")
    return ret


def get_pinpoints_journeys(pinpoint_project_id: str) -> Dict:
    print("Get pinpoint journey list")
    ret = pinpoint_client.list_journeys(ApplicationId=pinpoint_project_id)
    return dict((i['Name'], i['Id']) for i in ret['JourneysResponse']['Item'])


def validate_or_create_journey_for_client(pinpoint_project_id: str, client_id: int, segment_id: str) -> str:
    pinpoint_journeys = get_pinpoints_journeys(pinpoint_project_id=pinpoint_project_id)
    journey_name = f"{PINPOINT_JOURNEY_PREFIX}{client_id}"
    if f"{journey_name}" not in pinpoint_journeys:
        print("Create new journey")
        pinpoint_journey = create_pinpoint_journey(pinpoint_project_id=pinpoint_project_id, client_id=client_id,
                                                   segment_id=segment_id)
        print()
        return pinpoint_journey['JourneyResponse']['Id']

    else:
        print(f"Journey {journey_name} already created id: {pinpoint_journeys[journey_name]}")
        return pinpoint_journeys[journey_name]


def get_pinpoint_segments(pinpoint_project_id: str) -> Dict:
    ret = pinpoint_client.get_segments(
        ApplicationId=pinpoint_project_id
    )
    return ret['SegmentsResponse']['Item']


def get_segment_by_name(segment_name: str, pinpoint_project_id: str) -> Dict:
    all_segments = get_pinpoint_segments(pinpoint_project_id=pinpoint_project_id)
    for segment in all_segments:
        if segment['Name'] == segment_name:
            return segment
    return {}


def pinpoint_create_import_job(s3_path: str, client_id: int, pinpoint_project_id: str) -> Dict:
    selected_segment = get_segment_by_name(segment_name=f"segment_{client_id}", pinpoint_project_id=pinpoint_project_id)
    print(f"Selected segment: {selected_segment}")

    import_job_request = {
        "DefineSegment": True,
        "Format": "JSON",
        "S3Url": s3_path,
        "RoleArn": os.getenv("PINPOINT_ROLE_ARN"),
        "SegmentName": f"segment_{client_id}",
    }

    if selected_segment:
        print(f"Wil be updated existing segment with id: {selected_segment['Id']}")
        import_job_request["SegmentId"] = selected_segment['Id']

    ret = pinpoint_client.create_import_job(
        ApplicationId=pinpoint_project_id,
        ImportJobRequest=import_job_request
    )
    print(f"Import job created. Ret: {ret}")
    return ret


def set_in_journey_status_in_rds(debt_id):
    print("PROCESSED_DEBTS_ID", PROCESSED_DEBTS_ID)
    conn = create_db_connection()
    with closing(conn.cursor()) as cursor:
        cursor.executemany(f"UPDATE public.debt SET status={DBDebtStatus.in_journey.value} WHERE id= {debt_id};")
        conn.commit()


def handle_fail(journey_process_statuses: Dict[int, JourneyProcessStatusModel]):
    for portfolio_id in PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO:
        set_journey_process_status(status=JourneyProcessStatus.failed.value,
                                   journey_process_status=journey_process_statuses[portfolio_id])


def lambda_handler(event, context):
    print(f"Received event: {event}")

    params = event['Input']
    client_id = params['client_id']

    print(f"Run journey process update for {client_id} ")
    print("Get journey process statuses")
    journey_process_statuses = get_journey_process_statuses(client_id=client_id)

    print("Get borrower statuses")
    borrower_items = get_borrower_items(client_id=client_id, journey_process_statuses=journey_process_statuses)
    print(f"Found {len(borrower_items)} borrower_items records")
    s3_path = ""
    if borrower_items:
        try:
            s3_path = save_borrower_items_to_s3(client_id=client_id, borrower_items=borrower_items)
            print(f"Pinpoint segment JSON saved to: {s3_path}")
        except Exception as e:
            handle_fail(journey_process_statuses=journey_process_statuses)
            raise e

        if s3_path:
            try:
                import_job_ret = pinpoint_create_import_job(s3_path=s3_path, client_id=client_id,
                                                            pinpoint_project_id=os.getenv("AWS_PINPOINT_PROJECT_ID"))
                segment_id = import_job_ret['ImportJobResponse']['Definition']['SegmentId']
                pinpoint_journey_id = validate_or_create_journey_for_client(
                    pinpoint_project_id=os.getenv("AWS_PINPOINT_PROJECT_ID"), client_id=client_id,
                    segment_id=segment_id)

                for debt_id in PROCESSED_DEBTS_ID:
                    selected_segment = get_segment_by_name(segment_name=f"segment_{client_id}",
                                                           pinpoint_project_id=os.getenv("AWS_PINPOINT_PROJECT_ID"))
                    print(f"Selected segment: {selected_segment}")
                    if selected_segment:
                        journey_entry_activity_id = get_or_create_journey_entry_activity(journey_id=pinpoint_journey_id,
                                                                                         debt_id=debt_id)

                        print(f"Set in journey status in RDS for debt id: {debt_id}")
                        set_in_journey_status_in_rds(debt_id=debt_id)
                    else:
                        f"Could not find segment with name: segment_{client_id}. Skip journey creation"

            except Exception as e:
                handle_fail(journey_process_statuses=journey_process_statuses)
                raise e

        print("Set success status to DynamoDB")
        for portfolio_id in PROCESSED_JOURNEY_PROCESS_STATUSES_PORTFOLIO:
            set_journey_process_status(status=JourneyProcessStatus.success.value,
                                       journey_process_status=journey_process_statuses[portfolio_id])

    return {
        'statusCode': 200,
        'body': s3_path
    }

# if __name__ == "__main__":
# print(get_pinpoints_journeys('34e7ff51c4824c079b9ab87a6a530c2b'))
# validate_or_create_journey_for_client('34e7ff51c4824c079b9ab87a6a530c2b', 23, 'c40c83edb9be433e83f3cfc7f1e809ea')
# ret = pinpoint_create_import_job(s3_path='s3://chatbot-dev-clients-data/pinpoint_segments/client_id_1.json',
#                                  client_id=1, pinpoint_project_id='34e7ff51c4824c079b9ab87a6a530c2b')
# print(ret['ImportJobResponse']['Definition']['SegmentId'])
# print(ret['ImportJobResponse']['Definition']['S3Url'])
# print(ret)
# response = pinpoint_client.get_journey(
#     ApplicationId='34e7ff51c4824c079b9ab87a6a530c2b',
#     JourneyId='4b5ed88208fb4b1a85ceeb1d5ddf86d3'
# )
# print(response)
# lambda_handler({'Input': {'client_id': 69}}, {})

# PYTHONPATH=../common/python AWS_REGION=ca-central-1 AWS_PINPOINT_PROJECT_ID=34e7ff51c4824c079b9ab87a6a530c2b BASE_PATH=pinpoint_segments CLIENTS_S3_BUCKET_NAME=chatbot-dev-clients-data DBEndPoint=chatbot-dev-rds-proxy.proxy-cd4lkfqaythe.ca-central-1.rds.amazonaws.com DBUserName=superuser DYNAMODB_JOURNEY_PROCESS_STATUS_TABLE=chatbot-dev-journey-process-status DYNAMODB_MESSAGE_TABLE=chatbot-dev-messages DYNAMODB_SESSION_TABLE=chatbot-dev-sessions DatabaseName=symphony PINPOINT_ROLE_ARN=arn:aws:iam::630063752049:role/PinpointSegmentImport SQS_QUEUE_NAME=chatbot-devTaskQueue20210730121149213800000002 python3 app.py
