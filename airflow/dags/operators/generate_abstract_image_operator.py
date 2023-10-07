from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from PIL import Image, ImageDraw
import hashlib
import random
from pymongo import MongoClient
import io
import logging
from minio import Minio
from minio.error import S3Error
from bson import ObjectId

class GenerateAbstractImageOperator(BaseOperator):

    """
    Generates an abstract image based on the song text associated with a melody,
    stores the image in MinIO, and updates the MongoDB document with the MinIO URL.

    :param mongo_uri: MongoDB connection URI.
    :type mongo_uri: str
    :param mongo_db: MongoDB database name.
    :type mongo_db: str
    :param mongo_db_collection: MongoDB collection name for storing melody information.
    :type mongo_db_collection: str
    :param minio_endpoint: MinIO server endpoint URL.
    :type minio_endpoint: str
    :param minio_access_key: MinIO access key.
    :type minio_access_key: str
    :param minio_secret_key: MinIO secret key.
    :type minio_secret_key: str
    :param minio_bucket_name: MinIO bucket name for storing generated images.
    :type minio_bucket_name: str
    """

    
    @apply_defaults
    def __init__(
        self,
        mongo_uri,
        mongo_db,
        mongo_db_collection,
        minio_endpoint,
        minio_access_key,
        minio_secret_key,
        minio_bucket_name,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_db_collection = mongo_db_collection
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_bucket_name = minio_bucket_name

    def execute(self, context):
        logging.info("Starting execution of GenerateAbstractImageOperator")

        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_voice_task')['melody_id']
        logging.info(f"Retrieved melody_id: {melody_id}")

        # Connect to MongoDB and retrieve song text
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            melodies_collection = db[self.mongo_db_collection]

            melody_info = melodies_collection.find_one({"_id": ObjectId(melody_id)})
            song_text = melody_info.get("song_text")
            logging.info(f"Retrieved song text for melody_id: {melody_id}")

        # Define image dimensions
        image_size = (800, 600)

        # Create a new image with a white background
        image = Image.new("RGB", image_size, (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Use a hash of the song text to seed the random generation
        text_hash = int(hashlib.md5(song_text.encode()).hexdigest(), 16)
        random.seed(text_hash)

        # Generate abstract patterns with various shapes and colors
        num_shapes = 100
        for _ in range(num_shapes):
            shape_type = random.choice(["ellipse", "rectangle", "line"])
            x = random.randint(0, image_size[0])
            y = random.randint(0, image_size[1])
            size = random.randint(10, 100)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

            if shape_type == "ellipse":
                draw.ellipse([x, y, x + size, y + size], fill=color)
            elif shape_type == "rectangle":
                draw.rectangle([x, y, x + size, y + size], fill=color)
            elif shape_type == "line":
                end_x = random.randint(0, image_size[0])
                end_y = random.randint(0, image_size[1])
                draw.line([(x, y), (end_x, end_y)], fill=color, width=2)

        # Convert image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        # Store the generated abstract image in MinIO
        try:
            minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
            )
            image_object_name = f"{melody_id}_abstract_image.png"
            minio_client.put_object(
                bucket_name=self.minio_bucket_name,
                object_name=image_object_name,
                data=image_bytes,
                length=len(image_bytes.getvalue()),
                content_type="image/png",
            )
            logging.info(f"Abstract image stored in MinIO as {image_object_name}")
        except S3Error as e:
            logging.error(f"Error storing abstract image in MinIO: {e}")

        # Update the MongoDB document with the MinIO URL of the image
        image_url = minio_client.presigned_get_object(
            self.minio_bucket_name, image_object_name
        )
        logging.info(f"Image URL: {image_url}")

        # Update the document with the image URL
        melodies_collection.update_one(
            {"_id": ObjectId(melody_id)},
            {"$set": {"abstract_image_url": image_url}},
        )
        logging.info("Updated MongoDB document with image URL")

        logging.info("GenerateAbstractImageOperator execution completed")

        return {"melody_id": str(melody_id), "abstract_image_url": image_url}
