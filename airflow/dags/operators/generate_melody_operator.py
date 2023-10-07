from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from urllib.request import urlopen
from urllib.error import HTTPError
import os
import json
import gridfs
from pymongo import MongoClient
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
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.model_checkpoint_url = model_checkpoint_url
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection
        self.model_output_dir = model_output_dir

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

        # Get the song title and text from the configuration
        song_title = dag_run_conf['song_title']
        song_text = dag_run_conf['song_text']

        logging.info(f"Generating melody for '{song_title}' with text: {song_text}")

        # Initialize the MusicVAE model (with lazy import)
        lazy_import_magenta_music()
        model = mm.MusicVAE(self.model_output_dir)
        
        # Encode the text into a melody and generate the melody
        generated_melody = model.decode(model.encode([song_text]))[0]

        logging.info("Melody generated successfully")

        # Convert the generated melody to a MIDI file in memory
        lazy_import_magenta_midi_io()
        midi_data = midi_io.sequence_proto_to_midi_file(generated_melody)
        
        # Store the melody data, title, and text in MongoDB using GridFS
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        fs = gridfs.GridFS(db, collection=self.mongo_db_collection)
        melody_id = fs.put(midi_data, filename=f"{song_title}.midi", content_type="audio/midi", song_title=song_title, song_text=song_text)

        logging.info(f"Generated melody saved in MongoDB with ID: {melody_id}")
        logging.info("GenerateMelodyOperator execution completed")

        return {"melody_id": str(melody_id)}