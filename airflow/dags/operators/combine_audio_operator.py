from airflow.utils.decorators import apply_defaults
from pydub import AudioSegment
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
import tempfile

class CombineAudioOperator(BaseCustomOperator):

    """
    Combines a melody and voice audio and stores the combined audio in MinIO.

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

        # Get a reference to the MongoDB collection
        collection = self._get_mongodb_collection()

        melody_info = collection.find_one({"_id": ObjectId(melody_id)})
        melody_file_path = melody_info.get("melody_file_path")
        voice_file_path = melody_info.get("voice_file_path")

        self._log_to_mongodb(f"Retrieved melody WAV and voice audio paths for melody_id: {melody_id}", context, "INFO")

        # Connect to MinIO and download the Melody and voice audio
        minio_client = self._get_minio_client(context)

        try:
            melody_file_data = minio_client.get_object(self.minio_bucket_name, melody_file_path)
            voice_file_data = minio_client.get_object(self.minio_bucket_name, voice_file_path)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as melody_temp_file:
                melody_temp_file_path = melody_temp_file.name
                melody_temp_file.write(melody_file_data.read())

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as voice_temp_file:
                voice_temp_file_path = voice_temp_file.name
                voice_temp_file.write(voice_file_data.read())

            # Load the files using the file paths
            melody = AudioSegment.from_file(melody_temp_file_path, format="wav")
            voice = AudioSegment.from_file(voice_temp_file_path, format="wav")

            # Try to normalize the voice in order to improve the audio quality
            voice = voice.normalize()
            fade_duration = 100
            voice = voice.fade_in(fade_duration).fade_out(fade_duration)

            amplification_factor = 5.0
            melody = melody + amplification_factor
            voice = voice + amplification_factor
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
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as combined_audio_temp_file:
                combined_audio_temp_file_path = combined_audio_temp_file.name
                combined_audio.export(combined_audio_temp_file_path, format="mp4")

            final_song_path = f"{melody_id}_final_song.mp4"

            # Store the generated file in MinIO
            self._store_file_in_minio(
                local_file_path=combined_audio_temp_file_path, 
                minio_object_name=final_song_path,
                context=context, 
                content_type="audio/mpeg")

            self._log_to_mongodb(f"Combined audio stored in MinIO for melody_id: {melody_id}", context, "INFO")

            # Update the BSON document with the MinIO object path
            melody_info['final_song_path'] = final_song_path

            # Update the document in MongoDB
            collection.update_one({"_id": melody_info['_id']}, {"$set": melody_info})

            self._log_to_mongodb("CombineAudioOperator execution completed", context, "INFO")

        except Exception as e:
            self._log_to_mongodb(f"Error storing or retrieving audio from MinIO: {e}", context, "ERROR")
            raise

        return {"melody_id": str(melody_id)}
