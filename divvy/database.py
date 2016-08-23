"""Store and retrieve user data

This module interfaces with AWS's S3 to read and store user data
"""
import io
import json

import boto3
from botocore.exceptions import ClientError

from divvy import config

s3 = boto3.resource('s3', region_name=config.aws_region)
bucket = s3.Bucket(config.bucket_name)


def _keypath(user_id):
    return '%s/%s' % (config.key_prefix, user_id)


def put_user_data(user_id, **data):
    """Insert a new entry into the database.
    Any existing data for this user will be lost.
    """
    with io.BytesIO() as tmp:
        json.dump(data, tmp)
        tmp.seek(0)
        bucket.upload_fileobj(tmp, _keypath(user_id))
        return True


def update_user_data(user_id, **data):
    """Updates an existing user entry without changing
    any existing data associated with that user.
    If the user entry does not exist, it will be created.
    """
    user_data = get_user_data(user_id)
    user_data.update(data)
    put_user_data(user_id, **user_data)
    return True


def get_user_data(user_id):
    """Return all data associated with a given user ID.
    Returns an empty dictionary if the user does not exist.
    """
    with io.BytesIO() as tmp:
        try:
            bucket.download_fileobj(_keypath(user_id), tmp)
        except ClientError:
            # User not found
            return {}
        else:
            tmp.seek(0)
            return json.load(tmp)


def delete_user(user_id):
    """Entirely remove a user from the database
    """
    resp = bucket.Object(_keypath(user_id)).delete()
    return resp['ResponseMetadata']['HTTPStatusCode'] < 300
