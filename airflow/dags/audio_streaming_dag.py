from datetime import datetime
from airflow import DAG
import importlib
import os

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'logging_level': 'INFO'
}

# Create the DAG with the specified default arguments
with DAG('music_generation_dag', default_args=default_args, default_view="graph", schedule_interval=None, catchup=False) as dag:
    # Import the necessary operators from external modules
    operators_module = importlib.import_module('operators.generate_melody_operator')
    GenerateMelodyOperator = operators_module.GenerateMelodyOperator
    operators_module = importlib.import_module('operators.generate_voice_operator')
    GenerateVoiceOperator = operators_module.GenerateVoiceOperator
    operators_module = importlib.import_module('operators.generate_song_operator')
    GenerateSongOperator = operators_module.GenerateSongOperator
    operators_module = importlib.import_module('operators.generate_song_cover_operator')
    GenerateSongCoverOperator = operators_module.GenerateSongCoverOperator
    operators_module = importlib.import_module('operators.index_to_elasticsearch_operator')
    IndexToElasticsearchOperator = operators_module.IndexToElasticsearchOperator

    # Define the tasks for each operator
    generate_melody_task = GenerateMelodyOperator(
        task_id='generate_melody_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION"),
        minio_endpoint=os.environ.get("MINIO_ENDPOINT"),
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY"),
        minio_bucket_name=os.environ.get("MINIO_BUCKET_NAME")
    )

    generate_voice_task = GenerateVoiceOperator(
        task_id='generate_voice_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION"),
        minio_endpoint=os.environ.get("MINIO_ENDPOINT"),
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY"),
        minio_bucket_name=os.environ.get("MINIO_BUCKET_NAME")
    )

    generate_song_task = GenerateSongOperator(
        task_id='generate_song_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION"),
        minio_endpoint=os.environ.get("MINIO_ENDPOINT"),
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY"),
        minio_bucket_name=os.environ.get("MINIO_BUCKET_NAME")
    )

    generate_song_cover_operator = GenerateSongCoverOperator(
        task_id='generate_song_cover_operator',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION"),
        minio_endpoint=os.environ.get("MINIO_ENDPOINT"),
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY"),
        minio_bucket_name=os.environ.get("MINIO_BUCKET_NAME")
    )

    index_to_elasticsearch_operator = IndexToElasticsearchOperator(
        task_id='index_to_elasticsearch_operator',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION"),
        minio_endpoint=os.environ.get("MINIO_ENDPOINT"),
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY"),
        minio_bucket_name=os.environ.get("MINIO_BUCKET_NAME"),
        elasticsearch_host=os.environ.get("ELASTICSEARCH_HOST"),
        elasticsearch_index=os.environ.get("ELASTICSEARCH_INDEX")
    )

    # Define task dependencies by chaining the tasks in sequence
    generate_melody_task >> generate_voice_task >> generate_song_task >> generate_song_cover_operator >> index_to_elasticsearch_operator
