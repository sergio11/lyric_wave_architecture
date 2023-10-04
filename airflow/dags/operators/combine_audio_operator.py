# combine_audio_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from pydub import AudioSegment
from pymongo import MongoClient
import gridfs
import logging

class CombineAudioOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        mongo_uri,
        mongo_db,
        mongo_db_collection,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection

    def execute(self, context):
        logging.info("Starting execution of CombineAudioOperator")

        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_voice_task')['melody_id']
        logging.info(f"Retrieved melody_id: {melody_id}")

        # Connect to MongoDB and retrieve melody MIDI and voice audio
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            fs = gridfs.GridFS(db, collection=self.mongo_db_collection)

            melody_info = fs.find_one({"_id": melody_id})
            melody_midi_data = fs.get(melody_id).read()

            voice_audio_data = fs.get(melody_id).read()  # Replace this with actual field name
            logging.info(f"Retrieved melody MIDI and voice audio for melody_id: {melody_id}")

            # Load the melody MIDI and voice audio files
            melody = AudioSegment.from_file(melody_midi_data)
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
            logging.info("Audio files combined")

            # Export the combined audio as bytes
            combined_audio_data = combined_audio.export(format="mp3").read()
            logging.info("Combined audio exported as bytes")

            # Store the combined audio in MongoDB using GridFS
            combined_audio_id = fs.put(combined_audio_data, filename=f"{melody_id}_combined.mp3", content_type="audio/mpeg")
            logging.info(f"Combined audio stored in MongoDB with ID: {combined_audio_id}")

        logging.info("CombineAudioOperator execution completed")

        return {"melody_id": str(melody_id), "combined_audio_id": str(combined_audio_id)}
