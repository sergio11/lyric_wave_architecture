from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from gtts import gTTS
from pymongo import MongoClient
from bson import ObjectId
import io

class GenerateVoiceOperator(BaseCustomOperator):

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
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

    def execute(self, context):
        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_melody_task')['melody_id']
        self._log_to_mongodb(f"Retrieved melody_id: {melody_id}", context, "INFO")
        # Connect to MongoDB and retrieve song_text
        with MongoClient(self.mongo_uri) as client:
            self._log_to_mongodb(f"Connected to MongoDB", context, "INFO")
            db = client[self.mongo_db]
            collection = db[self.mongo_db_collection]
            
            melody_info = collection.find_one({"_id": ObjectId(melody_id)})
            song_text = melody_info.get("song_text")
            self._log_to_mongodb(f"Retrieved song_text from MongoDB: {song_text}", context, "INFO")
            # Generate speech from the song text using gTTS
            tts = gTTS(song_text)
            self._log_to_mongodb(f"Generated speech using gTTS", context, "INFO")
            
            # Save the speech to a file in MinIO
            # Get MinIO client
            minio_client = self._get_minio_client(context);

            try:
                speech_data_io = io.BytesIO()
                tts.save(speech_data_io)
                speech_data_bytes = speech_data_io.getvalue()
                speech_data_length = len(speech_data_bytes)
                self._log_to_mongodb(f"Speech data length: {speech_data_length}", context, "INFO")
                minio_client.put_object(
                    self.minio_bucket_name,
                    f"{melody_id}.mp3",
                    io.BytesIO(speech_data_bytes),  # Pass the bytes as a new BytesIO object
                    speech_data_length,  # Use the length of the bytes
                    content_type="audio/mpeg"
                )
                self._log_to_mongodb(f"Stored speech in MinIO bucket: {self.minio_bucket_name}", context, "INFO")
            except Exception as e:
                self._log_to_mongodb(f"Error storing speech in MinIO: {e}", context, "ERROR")
                raise

            # Update the BSON document with the MinIO object path
            melody_info['voice_map3_audio_path'] = f"{melody_id}.mp3"
            self._log_to_mongodb(f"Updated MongoDB document with voice_map3_audio_path", context, "INFO")
            # Update the document in MongoDB
            collection.update_one({"_id": melody_info['_id']}, {"$set": melody_info})
            self._log_to_mongodb(f"Updated MongoDB document with ID: {melody_id}", context, "INFO")
            return {"melody_id": str(melody_id)}