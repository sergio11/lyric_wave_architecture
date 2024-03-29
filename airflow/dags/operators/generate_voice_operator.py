from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
import importlib
import scipy
import tempfile
from datetime import datetime

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


    def _generate_voice(self, song_text): 
        """
        Generates voice from a given song text using the 'suno/bark' model.
        
        Args:
            song_text (str): The text of the song to be transformed into voice, which starts and ends with the musical note symbol "♪."
        
        Returns:
            str: The name of the generated voice audio file.

        This method uses the 'suno/bark' model from the Transformers library to convert the provided song text into voice. 
        The input song_text is expected to start and end with "♪," indicating the beginning and end of a musical performance. 
        By including these symbols, you provide explicit cues for the model to generate audio that is coherent with the musical context, 
        ensuring a smoother transition in the generated voice. The resulting audio is saved as a WAV file with a name based on the `song_id`.

        Returns the name of the generated voice audio file, which can be used to reference the stored audio.
        """
        # Add '♪' at the beginning and end of the song_text
        song_text_with_symbols = '♪' + song_text + '♪'
        transformers = importlib.import_module("transformers")
        processor = transformers.AutoProcessor.from_pretrained("suno/bark")
        model = transformers.BarkModel.from_pretrained("suno/bark")
        inputs = processor(song_text_with_symbols)
        audio_array = model.generate(**inputs)
        audio_array = audio_array.cpu().numpy().squeeze()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            wav_file_path = temp_file.name
            sample_rate = model.generation_config.sample_rate
            scipy.io.wavfile.write(wav_file_path, rate=sample_rate, data=audio_array)
        return wav_file_path

    def execute(self, context):
        # Retrieve song_id from the previous task using XCom
        song_id = context['task_instance'].xcom_pull(task_ids='generate_melody_task')['song_id']
        self._log_to_mongodb(f"Retrieved song_id: {song_id}", context, "INFO")

        collection = self._get_mongodb_collection()
        self._log_to_mongodb(f"Connected to MongoDB", context, "INFO")

        song_info = collection.find_one({"_id": ObjectId(song_id)})
        song_text = song_info.get("song_text")
        self._log_to_mongodb(f"Retrieved song_text from MongoDB: {song_text}", context, "INFO")
            
        try:
            self._log_to_mongodb(f"Generated speech using Suno Bark", context, "INFO")
            voice_file_path = self._generate_voice(song_text)
            self._log_to_mongodb("Voice generated successfully", context, "INFO")
        except Exception as e:
            error_message = f"An error occurred while generating the voice: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)
            
        self._log_to_mongodb(f"Storing voice in MinIO for '{song_id}'", context, "INFO")

        voice_file_name = f"{song_id}_voice.wav"
        # Store the generated .wav file in MinIO
        self._store_file_in_minio(
            local_file_path=voice_file_path, 
            minio_object_name=voice_file_name,
            context=context, 
            content_type="audio/wav")

        # Update the document in MongoDB
        collection.update_one({"_id": ObjectId(song_id)}, {
            "$set": {
                "voice_file_name": voice_file_name,
                "song_status": "voice_generated",
                "voice_generated_at": datetime.now()
            }
        })
        self._log_to_mongodb(f"Updated MongoDB document with voice_file_name: {voice_file_name}", context, "INFO")
        self._log_to_mongodb(f"Updated MongoDB document with ID: {song_id}", context, "INFO")
        return {"song_id": str(song_id)}
            
            