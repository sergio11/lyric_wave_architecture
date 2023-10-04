from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from generate_melody_operator import GenerateMelodyOperator
from generate_voice_operator import GenerateVoiceOperator
from combine_audio_operator import CombineAudioOperator
from generate_abstract_image_operator import GenerateAbstractImageOperator
import os

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

with DAG('music_generation_dag', default_args=default_args, schedule_interval=None, catchup=False) as dag:
    start_task = DummyOperator(task_id='start_task')

    generate_melody_task = GenerateMelodyOperator(
        task_id='generate_melody_task',
        model_checkpoint_url=os.environ.get("MODEL_CHECKPOINT_URL"),
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION")
    )

    generate_voice_task = GenerateVoiceOperator(
        task_id='generate_voice_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION")
    )

    combine_audio_task = CombineAudioOperator(
        task_id='combine_audio_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION")
    )

    generate_abstract_image_task = GenerateAbstractImageOperator(
        task_id='generate_abstract_image_task',
        mongo_uri=os.environ.get("MONGO_URI"),
        mongo_db=os.environ.get("MONGO_DB"),
        mongo_db_collection=os.environ.get("MONGO_DB_COLLECTION")
    )

    end_task = DummyOperator(task_id='end_task')

    start_task >> generate_melody_task >> generate_voice_task >> combine_audio_task >> generate_abstract_image_task >> end_task
