import json


def lambda_handler(event, context):
    print(event)
    print("check CD for lambda updates")
    print(event['Records'])
    """
    [{'EventSource': 'aws:sns', 
    'EventVersion': '1.0', 
    'EventSubscriptionArn': 'arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic:60affe38-2824-4f9d-a9a6-c00c186debf5', 
    'Sns': {'Type': 'Notification', 
            'MessageId': '166f4ff5-7d3e-56fc-9a03-1681d53578f2', 
            'TopicArn': 'arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic', 
            'Subject': None, 
            
            'Message': '{\n  "originationNumber":"+14255550182",\n  "destinationNumber":"+12125550101",\n  "messageKeyword":"JOIN",\n  "messageBody":"EXAMPLE",\n  "inboundMessageId":"cae173d2-66b9-564c-8309-21f858e9fb84",\n  "previousPublishedMessageId":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n}', 
            
            'Timestamp': '2021-07-23T11:19:39.334Z', 
            'SignatureVersion': '1', 
            'Signature': 'O+lemvM4TsYUQv+anEkYVt7ag82YwdAMudrSX8bq+MbSSuPeQp+aTSTCR0g3iUDCjwMtiLkUfP24hQxKzMNZD/YcP/Z9lXRGLrTdj2R9w70Le9AW9FOnQlPQ60VdcipOaSuzReU4SsW5prvhT4Jao2qctuSN6pHOILMSrVdmRAJdtwS/LDLVAZdMQFye3mSvLtPBzpz5z55XeCb8JfCoBvEsaZkflw2MIYE2FZ4gM+n+qXxKzWe4vmFzzBsrUJTQgdCUjxnnggqYQDzDTXhiVnqQ72WXRjJq9AwKTVwitPNbnG60AZIsmTfuT+703nTQ/ysVaT5o3jwQCPCc4sIYIA==', 
            'SigningCertUrl': 'https://sns.ca-central-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem', 
            'UnsubscribeUrl': 'https://sns.ca-central-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic:60affe38-2824-4f9d-a9a6-c00c186debf5', 
            'MessageAttributes': {}
            }
    }]
    """

    for record in event['Records']:
        if record.get('Sns'):
            response_msg = json.loads(record['Sns']['Message'])
            print(f"Response message from {response_msg['destinationNumber']}: {response_msg['messageKeyword']} {response_msg['messageBody']}")
