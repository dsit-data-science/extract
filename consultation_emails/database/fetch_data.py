"""
This module provides functionality to interact with S3 and DynamoDB, including uploading and downloading files.

Classes:
    StorageHandler: A class to handle downloading and uploading files from cloud platforms, specifically AWS.

Usage example:
    storage_handler = StorageHandler()
    print(storage_handler.load_file(blob="test_data/test.csv"))
    print(storage_handler.load_file(blob="test_data/test.json"))
    print(storage_handler.upload_data(local_file_path="your_file_path/test.csv, blob="test_data/test.csv"))
"""

import csv
import json
import os
from typing import Any, Union

import boto3
import pandas as pd
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError


class Session:
    """
    A class to represent a session for interacting with AWS services.
    Attributes
    ----------
    region : str
        The AWS region to use for the session. Defaults to the environment variable REGION.
    profile : str
        The AWS profile to use for the session. Defaults to the environment variable PROFILE.
    session : boto3.session.Session
        The boto3 session object initialized with the specified profile and region.
    Methods
    -------
    __init__():
        Initializes the session with the specified AWS profile and region.
    """

    def __init__(self, REGION: str = None, PROFILE: str = None) -> None:
        if REGION is None:
            REGION = os.environ["REGION"]
        if PROFILE is None:
            PROFILE = os.getenv("PROFILE", None)

        self.region = REGION
        if PROFILE:
            self.session = boto3.session.Session(profile_name=PROFILE, region_name=self.region)
        else:
            self.session = boto3.session.Session(region_name=self.region)


class StorageHandler(Session):
    """
    A handler for interacting with AWS S3, supporting file download and loading CSV/JSON files.
    """

    def __init__(
        self,
    ):
        """
        Initializes the StorageHandler.
        """
        super().__init__()
        self._s3_client = self.session.client("s3")

    def get_object(
        self,
        key: str,
        bucket: str = None
    ) -> dict:
        """
        Return the object from S3. Helpful for getting data for future processing when metadata is required.
        For full details see: "Response Syntax" > https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_object.html
        
        Args:
            key (str): The path of the file to download
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET if it's None.
        
        Returns:
            dict: Response data and metadata from S3
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]
        
        try:
            s3_object = self._s3_client.get_object(Bucket=bucket, Key=key)
        except self._s3_client.exceptions.NoSuchKey as e:
            error_message = f"Error. File not found in S3 bucket: {bucket + key}"
            raise KeyError(error_message) from e
        
        return s3_object

    def download_file(
        self,
        key: str,
        bucket: str = None,
        download_location: str = None,
        version_id: str = None,
    ) -> bool:
        """
        Downloads a file from S3.

        Args:
            key (str): The path of the file to download.
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET if it's None.
            download_location (str): The local path to save the file. Defaults to None.
            version_id (str): The version ID of the file. Defaults to None.
        Returns:
            bool: True if the file is downloaded successfully.
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]

        if download_location is None:
            download_location = key

        folder_path, _ = download_location.rsplit(sep="/", maxsplit=1)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        try:
            if version_id:
                self._s3_client.download_file(Bucket=bucket, Key=key, Filename=download_location, ExtraArgs={"VersionId": version_id})
            else:
                self._s3_client.download_file(Bucket=bucket, Key=key, Filename=download_location)
        except ClientError as e:
            print(f"Error downloading file from S3: {e}")
            return False

        return True

    def show_files(self, bucket: str = None) -> list[str]:
        """
        Lists the files in a bucket.

        Args:
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET if it's None.

        Returns:
            list[str]: A list of file names in the bucket.
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]
        return [key["Key"] for key in self._s3_client.list_objects(Bucket=bucket)["Contents"]]

    def load_csv(self, key: str, bucket: str = None, version_id: str = None) -> list[dict]:
        """
        Loads a CSV file from S3 into a list of dictionaries where each element is a row of the CSV

        Args:
            key (str): Location of the file within the bucket.
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET.
            version_id (str): The version ID of the file. Defaults to None.
        Returns:
            list[dict]: Each element is a row of the CSV
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]
        if not key.endswith(".csv"):
            raise TypeError(f"{key} not of type .csv")

        if version_id:
            response = self._s3_client.get_object(Bucket=bucket, Key=key, VersionId=version_id)
        else:
            response = self._s3_client.get_object(Bucket=bucket, Key=key)

        file_content = response["Body"].read().decode("utf-8")
        csv_data = []
        reader = csv.DictReader(file_content.splitlines())
        for row in reader:
            csv_data.append(row)

        return csv_data

    def load_json(self, key: str, bucket: str = None, version_id: str = None) -> dict:
        """
        Loads a JSON file from S3 into dictionary.

        Args:
            key (str): Location of the file within the bucket.
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET.
            version_id (str): The version ID of the file. Defaults to None.

        Returns:
            Dict: The loaded JSON data as a dictionary.
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]

        if not key.endswith(".json"):
            raise TypeError("`key` not of type .json")

        if version_id:
            response = self._s3_client.get_object(Bucket=bucket, Key=key, VersionId=version_id)
        else:
            response = self._s3_client.get_object(Bucket=bucket, Key=key)

        file_content = response["Body"].read().decode("utf-8")
        return json.loads(file_content)

    def load_jinja(self, key: str, bucket: str = None, version_id: str = None) -> str:
        """
        Loads a Jinja file from S3 into a string.

        Args:
            key (str): Location of the file within the bucket.
            bucket (str): The name of the bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET.
            version_id (str): The version ID of the file. Defaults to None.

        Returns:
            str: The loaded Jinja data as a string.
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]

        if not key.endswith(".jinja") or key.endswith(".jinja2"):
            raise TypeError("`key` not of type .jinja or .jinja2")

        if version_id:
            response = self._s3_client.get_object(Bucket=bucket, Key=key, VersionId=version_id)
        else:
            response = self._s3_client.get_object(Bucket=bucket, Key=key)

        return response["Body"].read().decode("utf-8")

    def upload_data(self, key: str, file_obj: Any, bucket: str = None) -> bool:
        """
        Uploads a file to S3.

        Args:
            key (str): The path to save the file in S3.
            local_file_path (str): The local path of the file to upload.
            bucket (str): The name of the S3 bucket. The default is the environment variable USER_UPLOAD_S3_BUCKET.

        Returns:
            bool: True if the file is uploaded successfully.
        """
        if bucket is None:
            bucket = os.environ["USER_UPLOAD_S3_BUCKET"]

        try:
            self._s3_client.upload_fileobj(file_obj, Bucket=bucket, Key=key)
            print(f"File uploaded to S3: {bucket}/{key}")
            return True
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            return False

class DynamoDbHandler(Session):
    """
    Initializes the DynamoDB connection and handles the data.
    """

    def __init__(
        self,
    ):
        super().__init__()
        self._dynamo_client = self.session.client("dynamodb")
        self._type_serialiser = TypeSerializer()

    def upload_data(self, data: dict, table_name: str = None) -> bool:
        """
        Uploads data to a DynamoDB table.

        Args:
            data (dict): The data to upload.
            table_name (str, optional): The name of the DynamoDB table. The default is the environment variable RESPONSES_TABLE_NAME.

        Returns (bool): True if the data is uploaded successfully.
        """
        if table_name is None:
            table_name = os.environ["RESPONSES_TABLE_NAME"]
        serialised_data = {k: self._type_serialiser.serialize(v) for k, v in data.items()}

        self._dynamo_client.put_item(TableName=table_name, Item=serialised_data)

        return True

    def query_partition_key(
        self, key: str, key_name: str = "response_id", table_name: str = None, limit: int = None, ascending: bool = True, deserialize=True
    ) -> list[dict]:
        """
        Queries a DynamoDB table based on the partition key.

        Args:
            key (str): The value of the partition key to query.
            key_name (str, optional): The name of the partition key. Defaults to "id".
            table_name (str, optional): The name of the DynamoDB table. The default is the environment variable RESPONSES_TABLE_NAME.
            limit (int, optional): Maximum number of items to return. Defaults to None (no limit).
            ascending (bool, optional): Whether to return items in ascending order by sort key value. Defaults to True.
            deserialize (bool, optional): Whether to deserialize the response. Defaults to True.

        Returns:
            list[dict]: The queried items from the DynamoDB table.
        """
        if table_name is None:
            table_name = os.environ["RESPONSES_TABLE_NAME"]
        query_args = {
            "TableName": table_name,
            "KeyConditionExpression": f"{key_name} = :key_value",
            "ExpressionAttributeValues": {":key_value": {"S": key}},
            "ScanIndexForward": ascending,
        }

        if limit is not None:
            query_args["Limit"] = limit

        response = self._dynamo_client.query(**query_args)

        if deserialize:
            deserializer = TypeDeserializer()
            return [{k: deserializer.deserialize(v) for k, v in element.items()} for element in response["Items"]]
        else:
            return response["Items"]

    def query_partition_key_sort_key(
        self,
        table_name,
        partition_key,
        sort_key,
        partition_value,
        sort_value,
        filter_key=None,
        filter_value=None,
        ascending=True,
        limit=None,
        deserialize=True,
    ):
        key_condition_expression = f"#{partition_key} = :partition_value AND #{sort_key} = :sort_value"
        expression_names = {f"#{partition_key}": partition_key, f"#{sort_key}": sort_key}
        expression_values = {":partition_value": {"S": partition_value}, ":sort_value": {"S": sort_value}}

        query_args = {
            "TableName": table_name,
            "KeyConditionExpression": key_condition_expression,
            "ExpressionAttributeNames": expression_names,
            "ExpressionAttributeValues": expression_values,
            "ScanIndexForward": ascending,
        }
        if limit is not None:
            query_args["Limit"] = limit

        if filter_key is not None and filter_value is not None:
            filter_expression = f"#{filter_key} = :filter_value"
            expression_names[f"#{filter_key}"] = filter_key
            expression_values[":filter_value"] = {"S": filter_value}
            query_args["FilterExpression"] = filter_expression

        response = self._dynamo_client.query(**query_args)

        if deserialize:
            deserializer = TypeDeserializer()
            return [{k: deserializer.deserialize(v) for k, v in element.items()} for element in response["Items"]]
        else:
            return response["Items"]

    def query_first_value(self, key: str, key_name: str = "response_id", table_name: str = None, deserialize=True) -> dict:
        """
        Queries the first value (lowest sort key value) for a given partition key.

        Args:
            key (str): The value of the partition key to query.
            key_name (str, optional): The name of the partition key. Defaults to "id".
            table_name (str, optional): The name of the DynamoDB table.
            deserialize (bool, optional): Whether to deserialize the response. Defaults to True.

        Returns:
            dict: The first item matching the partition key, or None if no items found.
        """
        if table_name is None:
            table_name = os.environ["RESPONSES_TABLE_NAME"]
        results = self.query_partition_key(key=key, key_name=key_name, table_name=table_name, limit=1, ascending=True, deserialize=deserialize)
        return results[0] if results else None

    def query_last_value(self, key: str, key_name: str = "response_id", table_name: str = None, deserialize=True) -> dict:
        """
        Queries the last value (highest sort key value) for a given partition key.

        Args:
            key (str): The value of the partition key to query.
            key_name (str, optional): The name of the partition key. Defaults to "id".
            table_name (str, optional): The name of the DynamoDB table.
            deserialize (bool, optional): Whether to deserialize the response. Defaults to True.

        Returns:
            dict: The last item matching the partition key, or None if no items found.
        """
        if table_name is None:
            table_name = os.environ["RESPONSES_TABLE_NAME"]
        results = self.query_partition_key(key=key, key_name=key_name, table_name=table_name, limit=1, ascending=False, deserialize=deserialize)
        return results[0] if results else None

    def get_all_items(self, table_name: str = None) -> list[dict]:
        """
        Gets all items from a DynamoDB table.

        Args:
            table_name (str): The name of the DynamoDB table. Defaults to RESPONSES_TABLE_NAME env var.

        Returns:
            list[dict]: List of all items in the table.
        """
        if table_name is None:
            table_name = os.environ["RESPONSES_TABLE_NAME"]

        paginator = self._dynamo_client.get_paginator("scan")
        items = []

        for page in paginator.paginate(TableName=table_name):
            if deserializer := TypeDeserializer():
                for item in page.get("Items", []):
                    items.append({k: deserializer.deserialize(v) for k, v in item.items()})

        return items

    def query_completed_responses(self, table_name: str) -> list[dict]:
        """
        Queries responses where completed=True using scan with filter.

        Args:
            table_name (str): The name of the DynamoDB table.

        Returns:
            list[dict]: List of completed response items.
        """
        paginator = self._dynamo_client.get_paginator("scan")
        filter_expression = "completed = :completed_value"
        expression_values = {":completed_value": {"BOOL": True}}

        items = []
        for page in paginator.paginate(TableName=table_name, FilterExpression=filter_expression, ExpressionAttributeValues=expression_values):
            if deserializer := TypeDeserializer():
                for item in page.get("Items", []):
                    items.append({k: deserializer.deserialize(v) for k, v in item.items()})

        return items


class SecretsManagerHandler(Session):
    """
    A handler for interacting with AWS Secrets Manager, supporting retrieval of secrets.
    """

    def __init__(
        self,
    ):
        super().__init__()
        self._secrets_manager = self.session.client("secretsmanager")
        self._cache = {}

    def _get_secret_dict(self, secret_id: str) -> dict:
        """
        Retrieves the secret dictionary from AWS Secrets Manager for a given secret ID.

        Args:
            secret_id (str): The ID of the secret to retrieve.

        Returns:
            dict: The secret value.
        """
        if secret_id in self._cache:
            return self._cache[secret_id]
        try:
            response = self._secrets_manager.get_secret_value(SecretId=secret_id)
            secret_dict = json.loads(response["SecretString"])
            self._cache[secret_id] = secret_dict
            return secret_dict
        except ClientError as e:
            raise RuntimeError(f"Failed to retrieve secret '{secret_id}': {str(e)}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Secret '{secret_id}' is not valid JSON.") from e

    def get_secret_value(self, secret_id: str, secret_key: str = None) -> Union[dict, Any]:
        """
        Retrieves the secret value from AWS Secrets Manager.

        Args:
            secret_id (str): The ID of the secret to retrieve.
            secret_key (str): The key of the secret value to retrieve. Defaults to None.

        Returns:
            Union[dict, Any]: Either a dictionary if a `secret_key` is not provided or the secret as in AWS Secrets Manager.
        """
        secret_dict = self._get_secret_dict(secret_id)
        if not secret_key:
            return secret_dict
        return secret_dict[secret_key]
    
class SsmHandler(Session):
    """
    A handler for interacting with AWS Systems Manager (SSM), supporting retrieval of parameters.
    """
    def __init__(
        self,
    ):
        super().__init__()
        self._ssm_client = self.session.client("ssm")
    
    def get_parameter(self, parameter_name: str) -> str:
        """
        Retrieves the value of a parameter from AWS SSM Parameter Store.

        Args:
            parameter_name (str): The name of the parameter to retrieve.

        Returns:
            str: The value of the parameter.
        """
        try:
            response = self._ssm_client.get_parameter(Name=parameter_name)
            return response["Parameter"]["Value"]
        except ClientError as e:
            raise RuntimeError(f"Failed to retrieve parameter '{parameter_name}': {e}") from e
        except KeyError as e:
            raise RuntimeError(f"Invalid response format for parameter '{parameter_name}': {e}") from e
