from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from pymongo import MongoClient
from bson import ObjectId
import importlib
import scipy

class GenerateVoiceOperator(BaseCustomOperator):

    """
        Custom Airflow operator for generating speech from song text using the 'suno/bark' model from the Transformers library,
        storing the speech in MinIO, and updating the BSON document in MongoDB with the MinIO object path.

        This operator retrieves song text and an associated melody_id from MongoDB, generates speech using the 'suno/bark' model
        from the Transformers library, saves the generated audio to MinIO, and updates the MongoDB document with the MinIO object
        path for the generated voice audio.

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


    def _generate_voice(self, melody_id, song_text): 
        """
        Generates voice from a given song text using the 'suno/bark' model.

        Args:
            melody_id (str): The unique identifier for the melody.
            song_text (str): The text of the song to be transformed into voice.

        Returns:
            str: The name of the generated voice audio file.

        This method uses the 'suno/bark' model from the Transformers library to convert the provided song text into voice.
        It saves the generated audio as a WAV file, and the file name is based on the `melody_id`.

        Returns the name of the generated voice audio file, which can be used to reference the stored audio.
        """
        transformers = importlib.import_module("transformers")
        processor = transformers.AutoProcessor.from_pretrained("suno/bark")
        model = transformers.BarkModel.from_pretrained("suno/bark")
        inputs = processor(song_text)
        audio_array = model.generate(**inputs)
        audio_array = audio_array.cpu().numpy().squeeze()
        sample_rate = model.generation_config.sample_rate
        voice_file_audio_name = f"{melody_id}_voice.wav"
        scipy.io.wavfile.write(voice_file_audio_name, rate=sample_rate, data=audio_array)
        return voice_file_audio_name

    def execute(self, context):
        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_melody_task')['melody_id']
        self._log_to_mongodb(f"Retrieved melody_id: {melody_id}", context, "INFO")

        collection = self._get_mongodb_collection()
        self._log_to_mongodb(f"Connected to MongoDB", context, "INFO")

        melody_info = collection.find_one({"_id": ObjectId(melody_id)})
        song_text = melody_info.get("song_text")
        self._log_to_mongodb(f"Retrieved song_text from MongoDB: {song_text}", context, "INFO")
            
        try:
            self._log_to_mongodb(f"Generated speech using Suno Bark", context, "INFO")
            voice_file_path = self._generate_voice(melody_id, song_text)
            self._log_to_mongodb("Voice generated successfully", context, "INFO")
        except Exception as e:
            error_message = f"An error occurred while generating the voice: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)
            
        self._log_to_mongodb(f"Storing voice in MinIO for '{melody_id}'", context, "INFO")

        # Store the generated .wav file in MinIO
        self._store_file_in_minio(
            local_file_path=voice_file_path, 
            minio_object_name=voice_file_path,
            context=context, 
            content_type="audio/wav")

        # Update the BSON document with the MinIO object path
        melody_info['voice_file_path'] = voice_file_path
        self._log_to_mongodb(f"Updated MongoDB document with voice_file_path: {voice_file_path}", context, "INFO")
        # Update the document in MongoDB
        collection.update_one({"_id": melody_info['_id']}, {"$set": melody_info})
        self._log_to_mongodb(f"Updated MongoDB document with ID: {melody_id}", context, "INFO")
        return {"melody_id": str(melody_id)}
            
            