import os

from ..beat_handler_process import BeatHandlerProcess

try:
    import winsound
    def beep(frequency, duration):
        winsound.Beep(frequency, duration)
except ImportError:
    def beep(frequency, duration):
        os.system(f"beep -f { frequency } -l { duration }")


class Beep(BeatHandlerProcess):

    NAME = "beep"

    def __init__(self, pipe, beats_only=False, onsets_only=False):
        BeatHandlerProcess.__init__(self, pipe)
        self.beats_only = beats_only
        self.onsets_only = onsets_only
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-b", "--beats-only", action="store_true", help="Only beep when beats are detected")
        parser.add_argument("-o", "--onsets-only", action="store_true", help="Only beep when onsets are detected")

    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(pipe, args, [], ["beats_only", "onsets_only"])

    def handle_beat(self):
        if self.onsets_only:
            return
        winsound.Beep(220, 20)

    def handle_onset(self):
        if self.beats_only:
            return
        winsound.Beep(440, 10)