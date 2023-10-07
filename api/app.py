from flask import Flask, request, jsonify, Response
import os
import requests
from pymongo import MongoClient
from bson import ObjectId
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MongoDB connection details from environment variables
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_DB_COLLECTION")

# Get Airflow DAG ID and API URL from environment variables
AIRFLOW_DAG_ID = os.environ.get("AIRFLOW_DAG_ID")
AIRFLOW_API_URL = os.environ.get("AIRFLOW_API_URL")

# Get API Executor username and password from environment variables
API_EXECUTOR_USERNAME = os.environ.get("API_EXECUTOR_USERNAME")
API_EXECUTOR_PASSWORD = os.environ.get("API_EXECUTOR_PASSWORD")

# Connect to MongoDB using the provided URI
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]

# Access the MongoDB collection for storing binary data
fs = db[MONGO_COLLECTION]

# Create a Flask application
app = Flask(__name__)

# Global error handler
@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"An error occurred: {str(e)}")
    return jsonify({"message": "An internal server error occurred"}), 500

# API endpoint for generating a song
@app.route('/generate_song', methods=['POST'])
def generate_song():
    logger.info("Received a request to generate a song.")
    
    try:
        # Get song title and text from the request's JSON data
        song_title = request.json.get('title')
        song_text = request.json.get('text')
        description = request.json.get('description')

        if song_title and song_text:
            logger.info(f"Generating song for '{song_title}' with description: {description}")

            # Generate a unique DAG run ID
            dag_run_id = str(uuid.uuid4())

            # Calculate the logical date 2 minutes from now
            logical_date = datetime.utcnow() + timedelta(minutes=2)
            logical_date_str = logical_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            # Build the URL to trigger the DAG execution
            airflow_dag_url = f"{AIRFLOW_API_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns"

            # Create a BSON document with song information
            song_info = {
                "song_title": song_title,
                "song_text": song_text,
                "description": description,
                "dag_run_id": dag_run_id,
                "logical_date": logical_date_str,
                "planned": False  # Initial status, not yet planned
            }

            # Insert the BSON document into MongoDB collection and get the ObjectID
            song_info_id = fs.insert_one(song_info).inserted_id

            logger.info(f"Inserted song information into MongoDB with ID: {song_info_id}")

            # Configure DAG run parameters
            dag_run_conf = {
                "conf": {
                    "song_info_id": str(song_info_id),
                },
                "dag_run_id": dag_run_id,
                "logical_date": logical_date_str,
                "note": f"Song generation for DAG run ID: {dag_run_id}"
            }

            # Trigger an Airflow DAG execution by sending a POST request
            response = requests.post(
                airflow_dag_url,
                json=dag_run_conf,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {API_EXECUTOR_USERNAME}:{API_EXECUTOR_PASSWORD}"
                }
            )

            if response.status_code == 200:
                # Update the BSON document with "planned" flag and date
                fs.update_one(
                    {"_id": song_info_id},
                    {"$set": {"planned": True, "planned_date": logical_date_str}}
                )

                logger.info("DAG execution triggered successfully")
                return jsonify({"message": "DAG execution triggered successfully"}), 200
            else:
                # If DAG execution failed, remove the document from MongoDB
                fs.delete_one({"_id": song_info_id})
                logger.error(f"Error triggering DAG execution: {response.text}")
                return jsonify({"message": "Error triggering DAG execution"}), 500
        else:
            logger.error("Missing title or text parameters")
            return jsonify({"message": "Missing title or text parameters"}), 400
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500

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
