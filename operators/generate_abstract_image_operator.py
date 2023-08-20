# generate_abstract_image_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from PIL import Image, ImageDraw
import hashlib
import random

class GenerateAbstractImageOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        song_text,
        output_image_path,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.song_text = song_text
        self.output_image_path = output_image_path

    def execute(self, context):
        # Define image dimensions
        image_size = (800, 600)

        # Create a new image with a white background
        image = Image.new("RGB", image_size, (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Use a hash of the song text to seed the random generation
        text_hash = int(hashlib.md5(self.song_text.encode()).hexdigest(), 16)
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

        # Save the generated abstract image
        image.save(self.output_image_path)