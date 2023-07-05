import logging
import multiprocessing

from .beat_tracker import BeatTracker

class BeatTrackerProcess(multiprocessing.Process, BeatTracker):

    FLAG_BEAT = 0
    FLAG_ONSET = 1
    FLAG_BPM = 2

    COMMAND_CONFIG = 0

    def __init__(self,
        config,
        audio_source,
        pipe,
        **kwargs
    ):
        self.pipe = pipe
        multiprocessing.Process.__init__(self)
        BeatTracker.__init__(self, config, audio_source, **kwargs)

    def send(self, flag, value=None):
        self.pipe.send((flag, self.frame_index, self.frame_index / self.sampling_rate_oss, value))

    def handle_beat(self):
        BeatTracker.handle_beat(self)
        if self.output_path is not None:
            self.output_file.flush()
        self.send(self.FLAG_BEAT)
    
    def handle_onset(self):
        BeatTracker.handle_onset(self)
        if self.output_path is not None:
            self.output_file.flush()
        self.send(self.FLAG_ONSET)
    
    def handle_bpm(self):
        BeatTracker.handle_bpm(self)
        if self.output_path is not None:
            self.output_file.flush()
        self.send(self.FLAG_BPM, self.bpm)
    
    def update_commands(self):
        while self.pipe.poll():
            command = self.pipe.recv()
            if command[0] == self.COMMAND_CONFIG:
                self.config.update(command[1], command[2])
                print("Updating configuration: %s=%s" % command)
            else:
                print("BeatTrackerProcess received an unknown command: %s" % command[0])

    def update(self):
        BeatTracker.update(self)
        self.update_commands()
    
    def run(self):
        log_format = "%(asctime)s\t%(levelname)s\tTracker: %(message)s"
        logging.basicConfig(level=logging.INFO, filename="beatviewer.log", format=log_format)
        logging.info("Starting beat tracker process with PID %d", self.pid)
        BeatTracker.run(self)
        logging.info("Beat tracker process has finished")