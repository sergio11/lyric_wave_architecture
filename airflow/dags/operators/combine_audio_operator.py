from airflow.utils.decorators import apply_defaults
from pydub import AudioSegment
from operators.base_custom_operator import BaseCustomOperator
from pymongo import MongoClient
from bson import ObjectId
from minio.error import S3Error
import io

class CombineAudioOperator(BaseCustomOperator):

    """
    CombineAudioOperator combines a melody MIDI file and voice audio file,
    and stores the combined audio in MinIO. It updates the BSON document in
    MongoDB with the MinIO object path for the combined audio.

    :param mongo_uri: MongoDB connection URI.
    :type mongo_uri: str
    :param mongo_db: MongoDB database name.
    :type mongo_db: str
    :param mongo_db_collection: MongoDB collection name.
    :type mongo_db_collection: str
    :param minio_endpoint: MinIO server endpoint.
    :type minio_endpoint: str
    :param minio_access_key: MinIO access key.
    :type minio_access_key: str
    :param minio_secret_key: MinIO secret key.
    :type minio_secret_key: str
    :param minio_bucket_name: MinIO bucket name.
    :type minio_bucket_name: str
    """
    @apply_defaults
    def __init__(
        self,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

    def execute(self, context):
        self._log_to_mongodb("Starting execution of CombineAudioOperator", context, "INFO")

        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_voice_task')['melody_id']
        self._log_to_mongodb(f"Retrieved melody_id: {melody_id}", context, "INFO")

        # Connect to MongoDB and retrieve melody MIDI and voice audio
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            collection = db[self.mongo_db_collection]

            melody_info = collection.find_one({"_id": ObjectId(melody_id)})
            melody_wav_file_path = melody_info.get("melody_wav_file_path")
            voice_map3_audio_path = melody_info.get("voice_map3_audio_path")
            self._log_to_mongodb(f"Retrieved melody WAV and voice audio paths for melody_id: {melody_id}", context, "INFO")

        # Connect to MinIO and download the WAV and voice audio
        # Get MinIO client
        minio_client = self._get_minio_client(context)

        try:
            with io.BytesIO() as melody_wav_data:
                minio_client.fget_object(self.minio_bucket_name, melody_wav_file_path, melody_wav_data)
                melody_wav_data.seek(0)

            with io.BytesIO() as voice_audio_data:
                minio_client.fget_object(self.minio_bucket_name, voice_map3_audio_path, voice_audio_data)
                voice_audio_data.seek(0)

            self._log_to_mongodb(f"Downloaded melody WAV and voice audio for melody_id: {melody_id}", context, "INFO")

            # Load the melody WAV and voice audio files
            melody = AudioSegment.from_file(melody_wav_data)
            voice = AudioSegment.from_file(voice_audio_data)

            # Resample the audio to match the same sample rate and channels
            voice = voice.set_frame_rate(melody.frame_rate)
            voice = voice.set_channels(melody.channels)

            # Ensure both audio files have the same duration
            if len(voice) > len(melody):
                melody += AudioSegment.silent(duration=len(voice) - len(melody))
            else:
                voice += AudioSegment.silent(duration=len(melody) - len(voice))

            # Combine the melody and voice
            combined_audio = melody.overlay(voice)
            self._log_to_mongodb("Audio files combined", context, "INFO")

            # Export the combined audio as bytes
            with io.BytesIO() as combined_audio_data:
                combined_audio.export(combined_audio_data, format="mp3")
                combined_audio_data.seek(0)

            # Store the combined audio in MinIO
            minio_client.put_object(
                self.minio_bucket_name,
                f"{melody_id}_combined.mp3",
                combined_audio_data,
                len(combined_audio_data),
                content_type="audio/mpeg"
            )
            self._log_to_mongodb(f"Combined audio stored in MinIO for melody_id: {melody_id}", context, "INFO")

            # Update the BSON document with the MinIO object path
            melody_info['combined_audio_path'] = f"{melody_id}_combined.mp3"

            # Update the document in MongoDB
            collection.update_one({"_id": melody_info['_id']}, {"$set": melody_info})

            self._log_to_mongodb("CombineAudioOperator execution completed", context, "INFO")

        except S3Error as e:
            self._log_to_mongodb(f"Error storing or retrieving audio from MinIO: {e}", context, "INFO")
            raise

        return {"melody_id": str(melody_id)}