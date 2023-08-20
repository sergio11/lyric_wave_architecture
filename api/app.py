from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

AIRFLOW_DAG_TRIGGER_URL = "http://webserver:8080/api/v1/dags/my_audio_generation_dag/dagRuns"

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
