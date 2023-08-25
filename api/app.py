from flask import Flask, request, jsonify
import os
from airflow.api.client.local_client import Client

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION")
AIRFLOW_DAG_ID = "audio_streaming_dag"

client = Client(None, None)

app = Flask(__name__)

@app.route('/generate_song', methods=['POST'])
def generate_song():
    song_title = request.json.get('title')
    song_text = request.json.get('text')

    if song_title and song_text:
        dag_run_conf = {
            "song_title": song_title,
            "song_text": song_text
        }

        client.trigger_dag(dag_id=AIRFLOW_DAG_ID, conf=dag_run_conf)
        return jsonify({"message": "DAG execution triggered successfully"}), 200
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
