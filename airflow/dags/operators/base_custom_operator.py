from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from pymongo import MongoClient
from minio import Minio
from datetime import datetime

class BaseCustomOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        mongo_uri,
        mongo_db,
        mongo_db_collection,
        minio_endpoint,
        minio_access_key,
        minio_secret_key,
        minio_bucket_name,
        *args, **kwargs
    ):
        """
        Initialize a custom base operator for common functionality.

        :param mongo_uri: The URI for the MongoDB connection.
        :param mongo_db: The name of the MongoDB database.
        :param mongo_db_collection: The name of the MongoDB collection.
        :param minio_endpoint: The MinIO server endpoint.
        :param minio_access_key: The access key for MinIO.
        :param minio_secret_key: The secret key for MinIO.
        :param minio_bucket_name: The name of the MinIO bucket.
        """
        super().__init__(*args, **kwargs)
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_bucket_name = minio_bucket_name

    def _log_to_mongodb(self, message, context, log_level):
        """
        Log a message to a MongoDB collection.

        :param message: The message to be logged.
        :param context: The execution context.
        :param log_level: The log level (e.g., INFO, ERROR).
        """
        task_instance = context['task_instance']
        task_instance_id = f"{task_instance.dag_id}.{task_instance.task_id}"
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_document = {
            "task_instance_id": task_instance_id,
            "log_level": log_level,
            "timestamp": current_timestamp,
            "log_message": message
        }
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        try:
            db.dags_execution_logs.insert_one(log_document)
            print("Log message registered in MongoDB")
        except Exception as e:
            print(f"Error writing log message to MongoDB: {e}")

    def _get_minio_client(self, context):
        """
        Get a MinIO client for interacting with MinIO.

        :param context: The execution context.

        :return: A MinIO client instance.
        """
        try:
            self._log_to_mongodb(f"MinIO Endpoint: {self.minio_endpoint}  Bucket Name: {self.minio_bucket_name}", context, "INFO")
            self._log_to_mongodb(f"Access Key: {self.minio_access_key}", context, "INFO")
            self._log_to_mongodb("Connecting to MinIO...", context, "INFO")
            minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=False
            )
            bucket_exists = minio_client.bucket_exists(self.minio_bucket_name)
            if not bucket_exists:
                self._log_to_mongodb(f"Bucket '{self.minio_bucket_name}' does not exist; creating...", context, "INFO")
                minio_client.make_bucket(self.minio_bucket_name)
            self._log_to_mongodb(f"Connected to MinIO and bucket '{self.minio_bucket_name}' exists", context, "INFO")
            return minio_client

        except Exception as e:
            error_message = f"Error connecting to MinIO: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)