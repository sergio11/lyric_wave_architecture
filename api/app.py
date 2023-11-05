from flask import Flask, request, jsonify, Response
import os
import requests
from pymongo import MongoClient
from bson import ObjectId
import uuid
from datetime import datetime, timedelta
import base64
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

@app.route('/music_styles', methods=['GET'])
def get_music_styles():
    try:
        # Retrieve the list of music styles from the collection
        music_styles_cursor = db['music_styles'].find({})
        styles = [{"style_id": str(style['_id']), "style_name": style['style']} for style in music_styles_cursor]
        response_data = {
            "status": "success",
            "code": 200,
            "message": "Music styles retrieved successfully." if styles else "No music styles found.",
            "music_styles": styles
        }
        return jsonify(response_data), 200
    except Exception as e:
        # Handle any exceptions and log errors
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500

@app.route('/music_styles', methods=['PUT'])
def update_music_styles():
    try:
        # Get the list of styles sent in the request
        styles = request.json.get('styles')
        if styles is not None:
            collection = db['music_styles']
            # Remove the existing music styles
            collection.delete_many({})

            # Insert each style as a separate document
            inserted_ids = []
            for style in styles:
                result = collection.insert_one({"style": style})
                inserted_ids.append(str(result.inserted_id))

            response_data = {
                "status": "success",
                "code": 200,
                "message": "Music styles updated successfully.",
                "inserted_ids": inserted_ids
            }
            return jsonify(response_data), 200
        else:
            response_data = {
                "status": "error",
                "code": 400,
                "message": "Invalid or missing 'styles' parameter in the request.",
            }
            return jsonify(response_data), 400
    except Exception as e:
        # Handle any exceptions and log errors
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500



# API endpoint for generating a song
@app.route('/generate_song', methods=['POST'])
def generate_song():
    logger.info("Received a request to generate a song.")

    try:
        # Get song title, text, description, keywords, and style ID from the request's JSON data
        song_title = request.json.get('title')
        song_text = request.json.get('text')
        description = request.json.get('description')
        keywords = request.json.get('keywords')
        music_style_id = request.json.get('music_style_id')

        # Validate the length of song_text
        validate_song_text(song_text)

        # Check if a song with the same title already exists
        check_existing_song(song_title)

        # Check if the provided style_id exists in the music_styles collection
        check_music_style(music_style_id)

        if song_title and song_text:
            logger.info(f"Generating song for '{song_title}' with description: {description}")

            # Generate a unique DAG run ID
            dag_run_id = str(uuid.uuid4())

            # Calculate the logical date 2 minutes from now
            logical_date = datetime.utcnow() + timedelta(minutes=2)
            logical_date_str = logical_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            # Build the URL to trigger the DAG execution
            airflow_dag_url = f"{AIRFLOW_API_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns"

            # Create a BSON document with song information, including keywords and style_id
            song_info = {
                "song_title": song_title,
                "song_text": song_text,
                "description": description,
                "keywords": keywords,
                "music_style_id": music_style_id,
                "dag_run_id": dag_run_id,
                "logical_date": logical_date_str,
                "planned": False  # Initial status, not yet planned
            }

            # Insert the BSON document into the MongoDB collection and get the ObjectID
            song_info_id = fs.insert_one(song_info).inserted_id

            logger.info(f"Inserted song information into MongoDB with ID: {song_info_id}")

            # Configure DAG run parameters, including song_info_id
            dag_run_conf = {
                "conf": {
                    "song_id": str(song_info_id),
                },
                "dag_run_id": dag_run_id,
                "logical_date": logical_date_str,
                "note": f"Song generation for DAG run ID: {dag_run_id}"
            }

            # Encode the API executor's username and password in Base64
            credentials = f"{API_EXECUTOR_USERNAME}:{API_EXECUTOR_PASSWORD}"
            credentials_base64 = base64.b64encode(credentials.encode()).decode()

            # Create headers for the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {credentials_base64}"
            }

            # Trigger an Airflow DAG execution by sending a POST request
            response = requests.post(
                airflow_dag_url,
                json=dag_run_conf,
                headers=headers
            )

            if response.status_code == 200:
                # Update the BSON document with "planned" flag and date
                fs.update_one(
                    {"_id": song_info_id},
                    {"$set": {"planned": True, "planned_date": logical_date_str}}
                )

                logger.info("DAG execution triggered successfully")
                response_data = {
                    "status": "success",
                    "code": 200,
                    "message": "Song generated and scheduled successfully.",
                    "song_info": {
                        "song_title": song_title,
                        "song_text": song_text,
                        "description": description,
                        "keywords": keywords,
                        "music_style_id": music_style_id,
                        "song_info_id": str(song_info_id),
                        "planned_date": logical_date_str
                    }
                }
                return jsonify(response_data), 200
            else:
                # If DAG execution failed, remove the document from MongoDB
                fs.delete_one({"_id": song_info_id})
                logger.error(f"Error triggering DAG execution: {response.text}")
                logger.error(f"HTTP Request Headers: {headers}")  # Log the request headers
                logger.error(f"HTTP Request Body: {dag_run_conf}")  # Log the request body
                response_data = {
                    "status": "error",
                    "code": response.status_code,
                    "message": "Error triggering DAG execution.",
                    "song_info": None
                }
                return jsonify(response_data), 500
        else:
            logger.error("Missing title or text parameters")
            response_data = {
                "status": "error",
                "code": 400,
                "message": "Missing title or text parameters.",
                "song_info": None
            }
            return jsonify(response_data), 400
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        response_data = {
            "status": "error",
            "code": 500,
            "message": "An internal server error occurred.",
            "song_info": None
        }
        return jsonify(response_data), 500

# API endpoint for retrieving a song by ID
@app.route('/songs/<string:song_id>', methods=['GET'])
def get_song_by_id(song_id):
    try:
        song_info = fs.find_one({"_id": ObjectId(song_id)})
        if song_info:
            response_data = {
                "status": "success",
                "code": 200,
                "message": "Song retrieved successfully.",
                "song_info": {
                    "song_title": song_info["song_title"],
                    "song_text": song_info["song_text"],
                    "description": song_info.get("description", ""),
                    "song_info_id": str(song_info["_id"]),
                    "planned_date": song_info.get("logical_date", "")
                }
            }
            return jsonify(response_data), 200
        else:
            response_data = {
                "status": "error",
                "code": 404,
                "message": "Song not found",
                "song_info": None
            }
            return jsonify(response_data), 404
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500

# API endpoint for listing all songs paginated, descending by date
@app.route('/songs', methods=['GET'])
def list_songs():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        songs = list(fs.find().sort([("logical_date", -1)]).skip((page - 1) * per_page).limit(per_page))
        if songs:
            response_data = {
                "status": "success",
                "code": 200,
                "message": "Songs retrieved successfully.",
                "songs": [
                    {
                        "song_title": song["song_title"],
                        "song_text": song["song_text"],
                        "description": song.get("description", ""),
                        "song_info_id": str(song["_id"]),
                        "planned_date": song.get("logical_date", "")
                    }
                    for song in songs
                ]
            }
            return jsonify(response_data), 200
        else:
            response_data = {
                "status": "error",
                "code": 404,
                "message": "No songs found",
                "songs": []
            }
            return jsonify(response_data), 404
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500

# API endpoint for deleting a song by ID
@app.route('/songs/<string:song_id>', methods=['DELETE'])
def delete_song_by_id(song_id):
    try:
        song_info = fs.find_one({"_id": ObjectId(song_id)})
        if song_info:
            fs.delete_one({"_id": ObjectId(song_id)})
            response_data = {
                "status": "success",
                "code": 200,
                "message": "Song deleted successfully",
                "song_info": {
                    "song_title": song_info["song_title"],
                    "song_text": song_info["song_text"],
                    "description": song_info.get("description", ""),
                    "song_info_id": str(song_info["_id"]),
                    "planned_date": song_info.get("logical_date", "")
                }
            }
            return jsonify(response_data), 200
        else:
            response_data = {
                "status": "error",
                "code": 404,
                "message": "Song not found",
                "song_info": None
            }
            return jsonify(response_data), 404
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"message": "An internal server error occurred"}), 500
    

# Helper function to validate song text length
def validate_song_text(song_text):
    max_length = 200
    if len(song_text) > max_length:
        return jsonify({"message": "Song text exceeds the maximum allowed length (200 characters)."}), 400

# Helper function to check if a song with the same title already exists
def check_existing_song(song_title):
    existing_song = fs.find_one({"song_title": song_title})
    if existing_song:
        return jsonify({"message": "A song with the same title already exists."}), 400

# Helper function to check if a music style with the specified ID exists
def check_music_style(style_id):
    try:
        style_id = ObjectId(style_id)
    except Exception:
        return jsonify({"message": "Invalid music style ID format. Must be a valid ObjectId."}), 400
    music_style = db['music_styles'].find_one({"_id": style_id})
    if not music_style:
        return jsonify({"message": "Invalid music style ID. The specified style does not exist."}), 400

# Start the Flask application if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
