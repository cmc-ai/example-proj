import json
from typing import Optional, Tuple, Generator, Dict
import re
import smart_open
from constants import HTTPCodes

NUM_COLUMNS = [0, 1, 2, 3, 7]


def split_csv_lines(data: str) -> Generator:
    return (x.group(0) for x in re.finditer(r"[^\n]+", data))


def is_num_value(value: str) -> bool:
    try:
        int(value)
        return True
    except Exception as e:
        print(e)
        return False


def validate_line(line: str) -> Tuple[Optional[bool], str]:
    columns = line.split(",")
    if len(columns) != 11:
        return False, "Incorrect columns number in a file"
    for i, c in enumerate(columns):
        if i in NUM_COLUMNS and not is_num_value(c):
            return False, f"Column {i} should have a numeric value"
    return True, ""


def upload(body: Dict, upload_s3_path: str):
    # print(f"Upload body: {body}")
    print(f"Upload S3 path: {upload_s3_path}")

    with smart_open.smart_open(upload_s3_path, 'w') as s3_out:
        for line in split_csv_lines(body):
            is_valid, err_str = validate_line(line=line)
            if not is_valid:
                return HTTPCodes.ERROR.value, {"message": f"Incorrect CSV file. {err_str}"}
            s3_out.write(f"{line}\n")

    return HTTPCodes.OK.value, {}

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
