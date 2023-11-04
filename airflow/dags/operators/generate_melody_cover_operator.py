from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
from diffusers import StableDiffusionPipeline
import torch

class GenerateMelodyCoverOperator(BaseCustomOperator):
    """
    Operator to generate a melody cover image from text using the Stable Diffusion model.

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
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

    def _generate_image_from_text(self, melody_id, song_text):
        """
        Generate an image based on the provided text using the Stable Diffusion model.

        :param melody_id: ID of the melody.
        :type melody_id: str
        :param song_text: Text description of the song.
        :type song_text: str
        :return: File path to the generated song cover image.
        :rtype: str
        """
        # Load the Stable Diffusion model using the specified checkpoint
        pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", torch_dtype=torch.float32)
        # Generate an image based on the provided text using the model
        image = pipe(song_text).images[0]
        song_cover_image = f"{melody_id}_cover.jpg"
        image.save(song_cover_image)
        return song_cover_image

    def execute(self, context):
        self._log_to_mongodb("Starting execution of GenerateAbstractImageOperator", context, "INFO")

        # Retrieve melody_id from the previous task using XCom
        melody_id = context['task_instance'].xcom_pull(task_ids='generate_voice_task')['melody_id']
        self._log_to_mongodb(f"Retrieved melody_id: {melody_id}", context, "INFO")

        # Get a reference to the MongoDB collection
        collection = self._get_mongodb_collection()
    
        melody_info = collection.find_one({"_id": ObjectId(melody_id)})
        song_text = melody_info.get("song_text")
        self._log_to_mongodb(f"Retrieved song text for melody_id: {melody_id}", context, "INFO")

        try:
            self._log_to_mongodb("Generating Song cover...", context, "INFO")
            song_cover_image = self._generate_image_from_text(melody_id, song_text)
            self._log_to_mongodb("Song cover generated successfully", context, "INFO")
        except Exception as e:
            error_message = f"An error occurred while generating the song cover: {e}"
            self._log_to_mongodb(error_message, context, "ERROR")
            raise Exception(error_message)
        
        # Store the generated .jpg file in MinIO
        self._store_file_in_minio(
            local_file_path=song_cover_image, 
            minio_object_name=song_cover_image,
            context=context, 
            content_type="image/jpeg")

        # Update the document with the song cover
        collection.update_one(
            {"_id": ObjectId(melody_id)},
            {"$set": {"song_cover_file": song_cover_image}},
        )
        self._log_to_mongodb("Updated MongoDB document with song cover", context, "INFO")
        self._log_to_mongodb("GenerateMelodyCoverOperator execution completed", context, "INFO")

        return {"melody_id": str(melody_id)}
