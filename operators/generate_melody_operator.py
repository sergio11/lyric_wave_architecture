# generate_melody_operator.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
import magenta.music as mm

class GenerateMelodyOperator(BaseOperator):
    @apply_defaults
    def __init__(
        self,
        song_text,
        model_checkpoint,
        output_midi_path,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.song_text = song_text
        self.model_checkpoint = model_checkpoint
        self.output_midi_path = output_midi_path

    def execute(self, context):
        # Initialize the MuseNet model
        model = mm.MusicVAE(self.model_checkpoint)

        # Encode the text into a melody and generate melody
        generated_melody = model.decode(model.encode([self.song_text]))[0]

        # Convert and save the generated melody as a MIDI file
        mm.midi_io.note_sequence_to_midi_file(generated_melody, self.output_midi_path)
