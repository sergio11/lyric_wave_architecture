from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
import importlib
import os

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

with DAG('music_generation_dag', default_args=default_args, default_view="graph", schedule_interval=None, catchup=False) as dag:
    start_task = DummyOperator(task_id='start_task')

    operators_module = importlib.import_module('operators.generate_melody_operator')
    GenerateMelodyOperator = operators_module.GenerateMelodyOperator
    operators_module = importlib.import_module('operators.generate_voice_operator')
    GenerateVoiceOperator = operators_module.GenerateVoiceOperator
    operators_module = importlib.import_module('operators.combine_audio_operator')
    CombineAudioOperator = operators_module.CombineAudioOperator
    operators_module = importlib.import_module('operators.generate_abstract_image_operator')
    GenerateAbstractImageOperator = operators_module.GenerateAbstractImageOperator

    generate_melody_task = GenerateMelodyOperator(
        task_id='generate_melody_task',
        model_checkpoint_url=os.environ.get("MODEL_CHECKPOINT_URL"),
        model_output_dir=os.environ.get("MODEL_OUTPUT_DIR"),
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
