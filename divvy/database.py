"""Store and retrieve user data

This module interfaces with AWS's DynamoDB to read and store user data
"""
import boto3
from botocore.exceptions import ClientError

from divvy import config


def _log_and_status(response):
    """If the response has an error code, print it.
    Return a boolean success flag.
    """
    if response.status_code >= 300:
        print(response.json())
        return False
    else:
        return True


def get_table():
    """Returns a reference to the table containing user data
    """
    dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
    table = dynamodb.Table(config.user_table)

    return table


def put_user_data(user_id, **data):
    """Insert a new entry into the database.
    Any existing data for this user will be lost.
    """
    tb = get_table()
    data['userId'] = user_id
    resp = tb.put_item(Item=data)

    return _log_and_status(resp)


def update_user_data(user_id, **data):
    """Updates an existing user entry without changing
    any existing data associated with that user.
    If the user entry does not exist, it will be created.
    """
    tb = get_table()
    attr = {k: {'Value': v, 'Action': 'PUT'} for k, v in data.items()}
    resp = tb.update_item(Key={'userId': user_id}, AttributeUpdates=attr)

    return _log_and_status(resp)


def get_user_data(user_id):
    """Return all data associated with a given user ID.
    Returns an empty dictionary if the user does not exist.
    """
    tb = get_table()
    try:
        response = tb.get_item(Key={'userId': user_id})
    except ClientError as e:
        print(e.response['Error']['Message'])
        raise
    else:
        _log_and_status(response)
        item = response.get('Item', {})

    return item


def delete_user(user_id):
    """Entirely remove a user from the database
    """
    tb = get_table()
    resp = tb.delete_item(Key={'userId': user_id})

    return _log_and_status(resp)
