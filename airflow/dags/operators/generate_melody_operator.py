from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
import importlib
import scipy
import tempfile
from datetime import datetime


class GenerateMelodyOperator(BaseCustomOperator):

    """
    Custom Airflow operator for generating musical melodies based on text input using AudioCraft by Facebook.

    This operator leverages a pre-trained model from Facebook's AudioCraft, encodes a given text input into a musical melody, 
    generates the melody, and stores it as a WAV audio file in a MinIO bucket. 
    It also updates the metadata in a MongoDB collection with the path to the generated audio file.

    :param mongo_uri: The MongoDB connection URI.
    :param mongo_db: The name of the MongoDB database.
    :param mongo_db_collection: The name of the MongoDB collection to store song information.
    :param minio_endpoint: The MinIO server endpoint.
    :param minio_access_key: The access key for MinIO.
    :param minio_secret_key: The secret key for MinIO.
    :param minio_bucket_name: The name of the MinIO bucket to store generated audio files.

    The operator is designed to be used within Airflow DAGs for music generation tasks.
    """
    @apply_defaults
    def __init__(
        self,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)


    def _generate_melody(self, song_text):
        """
        Generates a musical melody from the given song text using the AudioCraft by Facebook model.

        This function use the AudioCraft model to encode the provided song text into a musical melody.
        The generated melody is saved as a WAV audio file with a unique filename based on the song_id.

        Args:
            song_text (str): The text input used for generating the musical melody.

        Returns:
            str: The file path to the generated WAV audio file.
        """
        transformers = importlib.import_module("transformers")
        processor = transformers.AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = transformers.MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        inputs = processor(
            text=song_text,
            padding=True,
            return_tensors="pt",
        )
        audio_values = model.generate(**inputs, max_new_tokens=500)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            wav_file_path = temp_file.name
            sampling_rate = model.config.audio_encoder.sampling_rate
            scipy.io.wavfile.write(wav_file_path, rate=sampling_rate, data=audio_values[0, 0].numpy())
        return wav_file_path
    
    def _get_music_style_info(self, style_id):
        """
        Retrieves music style details based on the style_id from MongoDB's music_styles collection.

        Args:
            style_id (str): The music style ID to retrieve.

        Returns:
            dict: Music style details if found, or None.
        """
        collection = self._get_mongodb_collection(collection_name='music_styles')
        style_info = collection.find_one({"_id": ObjectId(style_id)})
        return style_info
        

    def execute(self, context):
        """
        Executes the GenerateMelodyOperator to generate and store a melody based on provided song information.

        Args:
            context (dict): The Airflow task context.

        Raises:
            Exception: If there's an error during the execution.

        This method is responsible for generating a melody based on song information, storing it in MinIO, and updating the song's
        document in MongoDB with the path to the generated melody. It performs several steps and handles errors appropriately.

        Args:
            context (dict): The Airflow task context containing information related to the task execution.

        Returns:
            dict: A dictionary containing information about the generated melody, specifically the melody's ID.
        """

        self._log_to_mongodb(f"Starting execution of GenerateMelodyOperator", context, "INFO")

        # Get the configuration passed to the DAG from the execution context
        dag_run_conf = context['dag_run'].conf

        # Get the song_info_id from the configuration
        song_id = dag_run_conf['song_id']
        self._log_to_mongodb(f"Received song_id: {song_id}", context, "INFO")

        # Get a reference to the MongoDB collection
        collection = self._get_mongodb_collection()
        self._log_to_mongodb("Connected to MongoDB", context, "INFO")

        song_info = collection.find_one({"_id": ObjectId(song_id)})
        if song_info is None:
            error_message = f"Song info with ID {song_id} not found in MongoDB"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)

        self._log_to_mongodb(f"Retrieved song info from MongoDB: {song_info}", context, "INFO")
        # Retrieve song title, text, and description from song_info
        song_title = song_info.get('song_title')
        song_text = song_info.get('song_text')

        # Retrieve music_style_id from song_info
        music_style_id = song_info.get('music_style_id')
    
        # Retrieve music style details from MongoDB
        style_info = self._get_music_style_info(music_style_id)

        if style_info:
            style_name = style_info.get('style_name')
            song_text = f"[{style_name}] {song_text}"
        else:
            self._log_to_mongodb("Music style not found in MongoDB", context, "WARNING")

        try:
            self._log_to_mongodb("Generating melody...", context, "INFO")
            melody_file_path = self._generate_melody(song_text)
            self._log_to_mongodb("Melody generated successfully", context, "INFO")
        except Exception as e:
            error_message = f"An error occurred while generating the melody: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)

        self._log_to_mongodb(f"Storing melody in MinIO for '{song_title}'", context, "INFO")

        melody_object_name = f"{song_id}_melody.wav"

        # Store the generated .wav file in MinIO
        self._store_file_in_minio(
            local_file_path=melody_file_path, 
            minio_object_name=melody_object_name,
            context=context, 
            content_type="audio/wav")

        # Update the existing BSON document
        collection.update_one({"_id": ObjectId(song_id)}, {
            "$set": {
                "melody_file_name": melody_object_name,
                "song_status": "melody_generated",
                "melody_generated_at": datetime.now()
            }
        })
        self._log_to_mongodb(f"Generated melody saved in MongoDB with ID: {song_id}", context, "INFO")
        self._log_to_mongodb("GenerateMelodyOperator execution completed", context, "INFO")

        return {"song_id": str(song_id)}
