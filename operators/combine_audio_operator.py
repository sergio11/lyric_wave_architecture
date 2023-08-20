# combine_audio_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from pydub import AudioSegment

class CombineAudioOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        melody_midi_path,
        voice_audio_path,
        output_song_path,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.melody_midi_path = melody_midi_path
        self.voice_audio_path = voice_audio_path
        self.output_song_path = output_song_path

    def execute(self, context):
        # Load the melody MIDI and voice audio files
        melody = AudioSegment.from_file(self.melody_midi_path)
        voice = AudioSegment.from_file(self.voice_audio_path)

        # Resample the audio to match the same sample rate and channels
        voice = voice.set_frame_rate(melody.frame_rate)
        voice = voice.set_channels(melody.channels)

        # Ensure both audio files have the same duration
        if len(voice) > len(melody):
            melody += AudioSegment.silent(duration=len(voice) - len(melody))
        else:
            voice += AudioSegment.silent(duration=len(melody) - len(voice))

        # Combine the melody and voice
        combined_audio = melody.overlay(voice)

        # Export the combined audio as the final song
        combined_audio.export(self.output_song_path, format="mp3")
