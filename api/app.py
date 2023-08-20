from flask import Flask, request, jsonify, Response
import requests
from pymongo import MongoClient
import gridfs
import os

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION")
# "http://webserver:8080/api/v1/dags/my_audio_generation_dag/dagRuns"
AIRFLOW_DAG_TRIGGER_URL = os.environ.get("AIRFLOW_DAG_TRIGGER_URL")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
fs = gridfs.GridFS(db, collection=MONGO_COLLECTION)

app = Flask(__name__)

@app.route('/generate_song', methods=['POST'])
def generate_song():
    song_title = request.json.get('title')
    song_text = request.json.get('text')

    if song_title and song_text:
        data = {
            "conf": {
                "song_title": song_title,
                "song_text": song_text
            }
        }

        response = requests.post(AIRFLOW_DAG_TRIGGER_URL, json=data)

        if response.status_code == 200:
            return jsonify({"message": "DAG execution triggered successfully"}), 200
        else:
            return jsonify({"message": "Failed to trigger DAG execution"}), 500
    else:
        return jsonify({"message": "Missing title or text parameters"}), 400

@app.route('/stream_audio/<song_id>')
def stream_audio(song_id):
    song = fs.find_one({"_id": ObjectId(song_id), "content_type": "audio/mpeg"})

    if song:
        def generate():
            data = song.read(1024)
            while data:
                yield data
                data = song.read(1024)

        response = Response(generate(), content_type=song.content_type)
        response.headers["Content-Disposition"] = f"inline; filename={song.filename}"
        return response

    return "Song not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
