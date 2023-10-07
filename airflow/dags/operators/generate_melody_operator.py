from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from urllib.request import urlopen
from urllib.error import HTTPError
import os
import json
from bson import ObjectId
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
import logging

def lazy_import_magenta_music():
    global mm
    if mm is None:
        import magenta.music as magenta_music
        mm = magenta_music

def lazy_import_magenta_midi_io():
    global midi_io
    if midi_io is None:
        from magenta.music import midi_io as magenta_midi_io
        midi_io = magenta_midi_io


class GenerateMelodyOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        model_checkpoint_url,
        model_output_dir,
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
        self.model_checkpoint_url = model_checkpoint_url
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection
        self.model_output_dir = model_output_dir
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_bucket_name = minio_bucket_name

    def _join_url(self, *parts):
        return '/'.join(parts)

    def _download_checkpoint(self, checkpoint_url, output_dir):
        try:
            response = urlopen(self._join_url(checkpoint_url, 'weights_manifest.json'))
        except HTTPError as e:
            self.log.error('Invalid checkpoint URL: %s', e.msg)
            return

        self.log.info('Downloaded weights manifest.')
        raw_manifest = response.read()
        open(os.path.join(output_dir, 'weights_manifest.json'), 'wb').write(raw_manifest)

        manifest = json.loads(raw_manifest)
        for p in manifest[0]['paths']:
            self.log.info('Downloading weights: `%s`.', p)
            try:
                response = urlopen(self._join_url(checkpoint_url, p))
            except HTTPError as e:
                self.log.error('Download failed, quitting: %s', e.msg)
                return
            open(os.path.join(output_dir, p), 'wb').write(response.read())

        self.log.info('Downloading config.')
        try:
            response = urlopen(self._join_url(checkpoint_url, 'config.json'))
        except HTTPError as e:
            self.log.info('No config present.')
        else:
            open(os.path.join(output_dir, 'config.json'), 'wb').write(response.read())

        self.log.info('Done.')

    def execute(self, context):
        logging.info("Starting execution of GenerateMelodyOperator")

        # Check if the model files are already downloaded
        if not os.path.exists(self.model_output_dir):
            self.log.info('Starting model download...')
            # Download model files using the provided URL
            self.download_checkpoint(self.model_checkpoint_url, self.model_output_dir)
            self.log.info('Model download complete.')

        # Get the configuration passed to the DAG from the execution context
        dag_run_conf = context['dag_run'].conf

        # Get the song_info_id from the configuration
        song_info_id = dag_run_conf['song_info_id']

        # Connect to MongoDB and retrieve song information
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        collection = db[self.mongo_db_collection]

        song_info = collection.find_one({"_id": ObjectId(song_info_id)})
        if song_info is None:
            raise Exception(f"Song info with ID {song_info_id} not found in MongoDB")

        # Retrieve song title, text, and description from song_info
        song_title = song_info.get('song_title')
        song_text = song_info.get('song_text')

        logging.info(f"Generating melody for '{song_title}'")

        # Initialize the MusicVAE model (with lazy import)
        lazy_import_magenta_music()
        model = mm.MusicVAE(self.model_output_dir)

        # Encode the text into a melody and generate the melody
        generated_melody = model.decode(model.encode([song_text]))[0]

        logging.info("Melody generated successfully")

        # Convert the generated melody to a MIDI file in memory
        lazy_import_magenta_midi_io()
        midi_data = midi_io.sequence_proto_to_midi_file(generated_melody)

        # Store the MIDI file in MinIO
        minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False  # True for secure connection (HTTPS)
        )

        try:
            minio_client.put_object(
                self.minio_bucket_name,
                f"{song_info_id}.midi",
                midi_data,
                len(midi_data),
                content_type="audio/midi"
            )
        except S3Error as e:
            logging.error(f"Error storing MIDI file in MinIO: {e}")
            raise

        # Update the existing BSON document with the path to the MIDI file in MinIO
        song_info['midi_file_path'] = f"{song_info_id}.midi"
 
        # Update the document in MongoDB
        collection.update_one({"_id": song_info['_id']}, {"$set": song_info})

        logging.info(f"Generated melody saved in MongoDB with ID: {song_info_id}")
        logging.info("GenerateMelodyOperator execution completed")

        return {"melody_id": str(song_info_id)}