from flask import Flask, request, jsonify, Response
import os
from airflow.api.client.local_client import Client
from pymongo import MongoClient
from bson import ObjectId

# Get MongoDB connection details from environment variables
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION")
AIRFLOW_DAG_ID = "audio_streaming_dag"

# Initialize an Airflow Client
client = Client(None, None)

# Connect to MongoDB using the provided URI
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]

# Access the MongoDB collection for storing binary data
fs = db[MONGO_COLLECTION]

# Create a Flask application
app = Flask(__name__)

# API endpoint for generating a song
@app.route('/generate_song', methods=['POST'])
def generate_song():
    # Get song title and text from the request's JSON data
    song_title = request.json.get('title')
    song_text = request.json.get('text')

    if song_title and song_text:
        # Configure DAG run parameters
        dag_run_conf = {
            "song_title": song_title,
            "song_text": song_text
        }

        # Trigger an Airflow DAG execution
        client.trigger_dag(dag_id=AIRFLOW_DAG_ID, conf=dag_run_conf)
        return jsonify({"message": "DAG execution triggered successfully"}), 200
    else:
        return jsonify({"message": "Missing title or text parameters"}), 400

# API endpoint for streaming audio by song ID
@app.route('/stream_audio/<song_id>')
def stream_audio(song_id):
    # Find the song document in MongoDB by its ID and content type
    song = fs.find_one({"_id": ObjectId(song_id), "content_type": "audio/mpeg"})

    if song:
        def generate():
            # Read and yield data from the song in chunks
            data = song.read(1024)
            while data:
                yield data
                data = song.read(1024)

        # Create a Flask Response for streaming audio
        response = Response(generate(), content_type=song.content_type)
        response.headers["Content-Disposition"] = f"inline; filename={song.filename}"
        return response

    return "Song not found", 404

# Start the Flask application if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
