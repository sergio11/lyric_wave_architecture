# generate_voice_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from gtts import gTTS
from pymongo import MongoClient
import gridfs

class GenerateVoiceOperator(BaseOperator):
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
        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_melody_task')['melody_id']
        
        # Connect to MongoDB and retrieve song_text
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            fs = gridfs.GridFS(db, collection=self.mongo_db_collection)
            
            melody_info = fs.find_one({"_id": melody_id})
            song_text = melody_info.get("song_text")

            # Generate speech from the song text using gTTS
            tts = gTTS(song_text)

            # Update the document with the audio of the TTS
            fs.put(tts.save(), _id=melody_id, content_type="audio/mpeg")

            return {"melody_id": str(melody_id)}

