# my_audio_generation_dag.py
from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from generate_operators import GenerateMelodyOperator, GenerateVoiceOperator
from combine_audio_operator import CombineAudioOperator
from generate_abstract_image_operator import GenerateAbstractImageOperator
from save_to_mongodb_operator import SaveToMongoDBOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

dag = DAG(
    'audio_generation_dag',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
)

start_task = DummyOperator(
    task_id='start',
    dag=dag,
)

generate_melody_task = GenerateMelodyOperator(
    task_id='generate_melody',
    song_text="This is the song lyrics...",
    model_checkpoint="path/to/musenet_checkpoint",
    output_midi_path="/path/to/output/generated_melody.mid",
    dag=dag,
)

generate_voice_task = GenerateVoiceOperator(
    task_id='generate_voice',
    song_text="This is the song lyrics...",
    output_audio_path="/path/to/output/generated_voice.mp3",
    dag=dag,
)

generate_abstract_image_task = GenerateAbstractImageOperator(
    task_id='generate_abstract_image',
    song_text="This is the song lyrics...",
    output_image_path="/path/to/output/abstract_image.png",
    dag=dag,
)

combine_audio_task = CombineAudioOperator(
    task_id='combine_audio',
    melody_midi_path="/path/to/output/generated_melody.mid",
    voice_audio_path="/path/to/output/generated_voice.mp3",
    output_song_path="/path/to/output/final_song.mp3",
    dag=dag,
)

save_to_mongodb_task = SaveToMongoDBOperator(
    task_id='save_to_mongodb',
    song_title="My Song Title",
    song_lyrics="This is the song lyrics...",
    melody_midi_path="/path/to/output/generated_melody.mid",
    voice_audio_path="/path/to/output/generated_voice.mp3",
    abstract_image_path="/path/to/output/abstract_image.png",
    final_song_path="/path/to/output/final_song.mp3",
    mongodb_uri="mongodb://localhost:27017/",
    mongodb_database="mydatabase",
    collection_name="songs",
    dag=dag,
)

end_task = DummyOperator(
    task_id='end',
    dag=dag,
)

start_task >> [generate_melody_task, generate_voice_task, generate_abstract_image_task]
generate_melody_task >> combine_audio_task
generate_voice_task >> combine_audio_task
generate_abstract_image_task >> combine_audio_task
combine_audio_task >> save_to_mongodb_task
save_to_mongodb_task >> end_task