# save_to_mongodb_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from pymongo import MongoClient
import json

class SaveToMongoDBOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        song_title,
        song_lyrics,
        melody_midi_path,
        voice_audio_path,
        abstract_image_path,
        final_song_path,
        mongodb_uri,
        mongodb_database,
        collection_name,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.song_title = song_title
        self.song_lyrics = song_lyrics
        self.melody_midi_path = melody_midi_path
        self.voice_audio_path = voice_audio_path
        self.abstract_image_path = abstract_image_path
        self.final_song_path = final_song_path
        self.mongodb_uri = mongodb_uri
        self.mongodb_database = mongodb_database
        self.collection_name = collection_name

    def execute(self, context):
        # Load the contents of the files
        with open(self.melody_midi_path, 'rb') as melody_file:
            melody_midi_data = melody_file.read()
        with open(self.voice_audio_path, 'rb') as voice_file:
            voice_audio_data = voice_file.read()
        with open(self.abstract_image_path, 'rb') as image_file:
            abstract_image_data = image_file.read()
        with open(self.final_song_path, 'rb') as final_song_file:
            final_song_data = final_song_file.read()

        # Create a JSON document
        song_document = {
            "title": self.song_title,
            "lyrics": self.song_lyrics,
            "melody_midi": melody_midi_data,
            "voice_audio": voice_audio_data,
            "abstract_image": abstract_image_data,
            "final_song": final_song_data,
        }

        # Connect to MongoDB
        client = MongoClient(self.mongodb_uri)
        database = client[self.mongodb_database]
        collection = database[self.collection_name]

        # Insert the document into the collection
        collection.insert_one(song_document)

        # Close the MongoDB connection
        client.close()