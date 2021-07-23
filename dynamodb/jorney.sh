aws dynamodb create-table \
    --table-name Jorneys \
    --attribute-definitions \
        AttributeName=JorneyID,AttributeType=I \
        AttributeName=BorrowerID,AttributeType=I \
        AttributeName=LexSession,AttributeType=S \
    --key-schema \
        AttributeName=JorneyID,KeyType=HASH \
        AttributeName=BorrowerID,KeyType=RANGE