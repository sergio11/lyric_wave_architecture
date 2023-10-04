# generate_abstract_image_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from PIL import Image, ImageDraw
import hashlib
import random
from pymongo import MongoClient
import gridfs
import io
import logging

class GenerateAbstractImageOperator(BaseOperator):
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
        logging.info("Starting execution of GenerateAbstractImageOperator")

        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_voice_task')['melody_id']
        logging.info(f"Retrieved melody_id: {melody_id}")

        # Connect to MongoDB and retrieve song text
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            fs = gridfs.GridFS(db, collection=self.mongo_db_collection)

            melody_info = fs.find_one({"_id": melody_id})
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

        # Store the generated abstract image in MongoDB using GridFS
        with MongoClient(self.mongo_uri) as client:
            db = client[self.mongo_db]
            fs = gridfs.GridFS(db, collection='melodies')

            abstract_image_id = fs.put(image_bytes, filename=f"{melody_id}_abstract_image.png", content_type="image/png")
            logging.info(f"Abstract image stored in MongoDB with ID: {abstract_image_id}")

        logging.info("GenerateAbstractImageOperator execution completed")

        return {"melody_id": str(melody_id), "abstract_image_id": str(abstract_image_id)}
