from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
from pymongo import MongoClient
import importlib
import scipy


class GenerateMelodyOperator(BaseCustomOperator):

    """
    Custom Airflow operator for generating melodies based on text input using Magenta's MusicVAE.

    This operator downloads a pre-trained Magenta MusicVAE model checkpoint, encodes a given
    text input into a musical melody, generates the melody, and stores it as a MIDI file
    in a MinIO bucket. It also updates the metadata in a MongoDB collection with the path
    to the generated MIDI file.

    :param mongo_uri: The MongoDB connection URI.
    :param mongo_db: The name of the MongoDB database.
    :param mongo_db_collection: The name of the MongoDB collection to store song information.
    :param minio_endpoint: The MinIO server endpoint.
    :param minio_access_key: The access key for MinIO.
    :param minio_secret_key: The secret key for MinIO.
    :param minio_bucket_name: The name of the MinIO bucket to store generated MIDI files.

    The operator is designed to be used within Airflow DAGs for music generation tasks.
    """
    @apply_defaults
    def __init__(
        self,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)


    def _generate_melody(self, song_info_id, song_text):
        """
        Generate a musical melody from the given song text using a pre-trained Magenta MusicVAE model.

        This private method takes the provided song text, processes it using a pre-trained
        MusicVAE model, and generates a musical melody. The generated melody is saved as a WAV file.

        :param song_info_id: The unique identifier associated with the song information.
        :param song_text: The input text used for melody generation.
        
        :return: The file path of the generated WAV file.
        
        This function uses the 'facebook/musicgen-small' model to generate the melody. It pads
        the input text, returns the tensor representation, and generates the audio values. The
        resulting melody is saved as a WAV file with a file name derived from 'song_info_id'.

        Example:
        ::
        
            melody_path = _generate_melody(song_id, "Once upon a time in a distant land...")
            # melody_path could be something like '605c1b6d20095cd4338d12c7.wav'

        """
        transformers = importlib.import_module("transformers")
        processor = transformers.AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = transformers.MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        inputs = processor(
            text=song_text,
            padding=True,
            return_tensors="pt",
        )
        audio_values = model.generate(**inputs, max_new_tokens=150)
        wav_file_path = f"{song_info_id}.wav"
        sampling_rate = model.config.audio_encoder.sampling_rate
        scipy.io.wavfile.write(wav_file_path, rate=sampling_rate, data=audio_values[0, 0].numpy())
        return wav_file_path

    def execute(self, context):
        self._log_to_mongodb("Starting execution of GenerateMelodyOperator", context, "INFO")

        # Get the configuration passed to the DAG from the execution context
        dag_run_conf = context['dag_run'].conf

        # Get the song_info_id from the configuration
        song_info_id = dag_run_conf['song_info_id']
        self._log_to_mongodb(f"Received song_info_id: {song_info_id}", context, "INFO")

        # Connect to MongoDB and retrieve song information
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        collection = db[self.mongo_db_collection]
        self._log_to_mongodb("Connected to MongoDB", context, "INFO")

        song_info = collection.find_one({"_id": ObjectId(song_info_id)})
        if song_info is None:
            error_message = f"Song info with ID {song_info_id} not found in MongoDB"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)
        
        self._log_to_mongodb(f"Retrieved song info from MongoDB: {song_info}", context, "INFO")
        # Retrieve song title, text, and description from song_info
        song_title = song_info.get('song_title')
        song_text = song_info.get('song_text')

        # Get MinIO client
        minio_client = self._get_minio_client(context);

        try:
            self._log_to_mongodb("Generating melody...", context, "INFO")
            wav_file_path = self._generate_melody(song_info_id, song_text)
            self._log_to_mongodb("Melody generated successfully", context, "INFO")
        except Exception as e:
            error_message = f"An error occurred while generating the melody: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)
        
        self._log_to_mongodb(f"Storing melody in MinIO for '{song_title}'", context, "INFO")

        try:
            with open(wav_file_path, 'rb') as file_data:
                file_data.seek(0, 2)  # Ir al final del archivo para obtener el tamaño en bytes
                file_size_bytes = file_data.tell()
                file_data.seek(0)  # Volver al principio
                
                if file_size_bytes == 0:
                    error_message = "WAV file is empty"
                    self._log_to_mongodb(error_message, context, "ERROR")
                    raise Exception(error_message)
                
                file_size_kb = file_size_bytes / 1024
                self._log_to_mongodb(f"Try to store Melody file ({file_size_kb:.2f} KB) in MinIO bucket: {self.minio_bucket_name}", context, "INFO")
                
                minio_client.put_object(
                    self.minio_bucket_name,
                    wav_file_path,
                    file_data,
                    file_size_bytes,
                    content_type="audio/wav"
                )
                self._log_to_mongodb(f"Melody file stored in MinIO bucket: {self.minio_bucket_name}", context, "INFO")
        except Exception as e:
            error_message = f"Error storing WAV file in MinIO: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)

        # Update the existing BSON document with the path to the WAV file in MinIO
        song_info['melody_wav_file_path'] = wav_file_path
 
        # Update the document in MongoDB
        collection.update_one({"_id": song_info['_id']}, {"$set": song_info})

        self._log_to_mongodb(f"Generated melody saved in MongoDB with ID: {song_info_id}", context, "INFO")
        self._log_to_mongodb("GenerateMelodyOperator execution completed", context, "INFO")

        return {"melody_id": str(song_info_id)}