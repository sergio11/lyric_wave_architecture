from flask import Flask, Response, app, request
from pymongo import MongoClient
from bson import ObjectId
from minio import Minio
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MongoDB connection details from environment variables
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_DB_COLLECTION")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = os.environ.get("MINIO_BUCKET_NAME")

# Connect to MongoDB using the provided URI
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
songs_collection = db[MONGO_COLLECTION]

app = Flask(__name__)

@app.route('/stream_melody/<string:song_id>', methods=['GET'])
def stream_melody(song_id):
    """
    Stream the melody of a song identified by song_id.

    Args:
        song_id (str): The unique identifier of the song.

    Returns:
        Response: A response object that streams the melody audio file.
    """
    song_info = songs_collection.find_one({"_id": ObjectId(song_id)})
    if song_info:
        return _stream_file_from_minio(song_info, MINIO_BUCKET_NAME, "melody_file_name", "audio/wav", "melody.wav")
    else:
        return "Song not found", 404

@app.route('/stream_voice/<string:song_id>', methods=['GET'])
def stream_voice(song_id):
    """
    Stream the voice of a song identified by song_id.

    Args:
        song_id (str): The unique identifier of the song.

    Returns:
        Response: A response object that streams the voice audio file.
    """
    song_info = songs_collection.find_one({"_id": ObjectId(song_id)})
    if song_info:
        return _stream_file_from_minio(song_info, MINIO_BUCKET_NAME, "voice_file_name", "audio/wav", "voice.wav")
    else:
        return "Song not found", 404

@app.route('/stream_song/<string:song_id>', methods=['GET'])
def stream_song(song_id):
    """
    Stream the complete song of a song identified by song_id.

    Args:
        song_id (str): The unique identifier of the song.

    Returns:
        Response: A response object that streams the complete song audio file.
    """
    song_info = songs_collection.find_one({"_id": ObjectId(song_id)})
    if song_info:
        return _stream_file_from_minio(song_info, MINIO_BUCKET_NAME, "final_song_name", "audio/mpeg", "final_song_name.mp4")
    else:
        return "Song not found", 404

@app.route('/show_image/<string:song_id>', methods=['GET'])
def show_image(song_id):
    """
    Show the image associated with a song identified by song_id.

    Args:
        song_id (str): The unique identifier of the song.

    Returns:
        Response: A response object that displays the image file.
    """
    song_info = songs_collection.find_one({"_id": ObjectId(song_id)})
    if song_info:
        return _stream_file_from_minio(song_info, MINIO_BUCKET_NAME, "song_cover_name", "image/jpeg", "image.jpg")
    else:
        return "Song not found", 404

def _stream_file_from_minio(song_info, minio_bucket_name, file_key, content_type, file_extension):
    """
    Stream a file from MinIO.

    Args:
        song_info (dict): Information about the song.
        minio_bucket_name (str): The name of the MinIO bucket.
        file_key (str): The key of the file in MinIO.
        content_type (str): The content type of the file.
        file_extension (str): The file extension.

    Returns:
        Response: A response object that streams the file data.
    """
    try:
        # Retrieve the file path from MinIO
        minio_client = _get_minio_client()
        file_data = minio_client.get_object(minio_bucket_name, song_info[file_key])

        # Define response headers for streaming audio
        headers = {
            'Content-Type': content_type,
            'Cache-Control': 'no-store',
            'Content-Disposition': f'inline; filename="{song_info[file_key]}.{file_extension}"',
            'Accept-Ranges': 'none'
        }

        # Generator function to stream the file data in chunks
        def generate():
            for data in file_data.stream(1024):
                yield data

        return Response(generate(), headers=headers, status=200)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return "An error occurred", 500

def _get_minio_client():
    """
    Create a MinIO client and ensure the bucket exists.

    Returns:
        Minio: A MinIO client instance.
    """
    try:
        minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        bucket_exists = minio_client.bucket_exists(MINIO_BUCKET_NAME)
        if not bucket_exists:
            minio_client.make_bucket(MINIO_BUCKET_NAME)
        return minio_client
    except Exception as e:
        error_message = f"Error connecting to MinIO: {e}"
        raise Exception(error_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
