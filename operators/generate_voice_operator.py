# generate_voice_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from gtts import gTTS
import os

class GenerateVoiceOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        song_text,
        output_audio_path,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.song_text = song_text
        self.output_audio_path = output_audio_path

    def execute(self, context):
        # Generate speech from the song text using gTTS
        tts = gTTS(self.song_text)
        tts.save(self.output_audio_path)
