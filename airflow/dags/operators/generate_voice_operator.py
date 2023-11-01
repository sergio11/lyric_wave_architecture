from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from gtts import gTTS
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
from bson import ObjectId
import io
import logging

class GenerateVoiceOperator(BaseOperator):

    """
    Custom Airflow operator to generate speech from song text using gTTS, store the speech in MinIO,
    and update the BSON document in MongoDB with the MinIO object path.
    
    :param mongo_uri: MongoDB connection URI.
    :param mongo_db: MongoDB database name.
    :param mongo_db_collection: MongoDB collection name where BSON documents are stored.
    :param minio_endpoint: MinIO server endpoint.
    :param minio_access_key: MinIO server access key.
    :param minio_secret_key: MinIO server secret key.
    :param minio_bucket_name: MinIO bucket name for storing speech files.
    """

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
        super().__init__(*args, **kwargs)
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_bucket_name = minio_bucket_name

    def execute(self, context):
        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_melody_task')['melody_id']
        
        # Connect to MongoDB and retrieve song_text
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            collection = db[self.mongo_db_collection]
            
            melody_info = collection.find_one({"_id": ObjectId(melody_id)})
            song_text = melody_info.get("song_text")

            # Generate speech from the song text using gTTS
            tts = gTTS(song_text)

            # Save the speech to a file in MinIO
            minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=False  # Change to True for secure connection (HTTPS)
            )

            try:
                # Get the bytes stored in the _io.BytesIO object
                speech_data_bytes = tts.get_data()

                # Use len() to get the length of the bytes
                speech_data_length = len(speech_data_bytes)

                minio_client.put_object(
                    self.minio_bucket_name,
                    f"{melody_id}.mp3",
                    io.BytesIO(speech_data_bytes),  # Pass the bytes as a new BytesIO object
                    speech_data_length,  # Use the length of the bytes
                    content_type="audio/mpeg"
                )
            except S3Error as e:
                logging.error(f"Error storing speech in MinIO: {e}")
                raise

            # Update the BSON document with the MinIO object path
            melody_info['voice_map3_audio_path'] = f"{melody_id}.mp3"

            # Update the document in MongoDB
            collection.update_one({"_id": melody_info['_id']}, {"$set": melody_info})

            return {"melody_id": str(melody_id)}