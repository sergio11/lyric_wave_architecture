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

    def _get_mongodb_collection(self, collection_name=None):
        """
        Private method to securely obtain a reference to the MongoDB collection.

        Args:
            collection_name (str, optional): The name of the MongoDB collection to retrieve. If not provided, the default collection is used.

        Returns:
            pymongo.collection.Collection: A reference to the desired MongoDB collection.
        """
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        
        if collection_name:
            return db[collection_name]
        else:
            return db[self.mongo_db_collection]

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
        

    def _store_file_in_minio(self, local_file_path, minio_object_name, context, content_type=None):
        """
        Stores a file in MinIO.

        Args:
            local_file_path (str): The local path to the file to be stored in MinIO.
            minio_object_name (str): The name to be used for the object in MinIO.
            context (dict): The Airflow task context for logging and error handling.
            content_type (str, optional): The content type of the object to be stored in MinIO.

        Raises:
            Exception: If there's an error during the MinIO file storage process.

        This method is responsible for uploading a file to a specified MinIO bucket. It checks the file's
        size, sets the content type if specified, and logs information about the storage process. If an error occurs,
        it raises an exception with an error message.

        Args:
            local_file_path (str): The local path to the file.
            minio_object_name (str): The name for the object in MinIO.
            context (dict): The Airflow task context.
            content_type (str, optional): The content type of the object.

        Returns:
            None
        """
        try:
            with open(local_file_path, 'rb') as file_data:
                file_data.seek(0, 2)
                file_size_bytes = file_data.tell()
                file_data.seek(0)
                if file_size_bytes == 0:
                    error_message = f"File '{local_file_path}' is empty"
                    self._log_to_mongodb(error_message, context, "ERROR")
                    raise Exception(error_message)
                
                file_size_kb = file_size_bytes / 1024
                self._log_to_mongodb(f"Try to store file '{local_file_path}' ({file_size_kb:.2f} KB) in MinIO bucket: {self.minio_bucket_name}", context, "INFO")
                 # Get MinIO client
                minio_client = self._get_minio_client(context)
                minio_client.put_object(
                    self.minio_bucket_name,
                    minio_object_name,
                    file_data,
                    file_size_bytes,
                    content_type=content_type
                )
                self._log_to_mongodb(f"File '{local_file_path}' stored in MinIO bucket: {self.minio_bucket_name}", context, "INFO")
        except Exception as e:
            error_message = f"Error storing file '{local_file_path}' in MinIO: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)