import logging
import multiprocessing

from .beat_tracker_process import BeatTrackerProcess


class BeatHandlerProcess(multiprocessing.Process):

    NAME = "default"

    def __init__(self, pipe):
        self.pipe = pipe
        self.running = True
        super(BeatHandlerProcess, self).__init__()
        logging.info("Using beat handler class %s", self.__class__.__name__)

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_args(cls, pipe, args):
        return cls(pipe)

    @classmethod
    def from_keys(cls, pipe, args, args_keys, kwargs_keys):
        return cls(pipe, *[getattr(args, key) for key in args_keys], **{key: getattr(args, key) for key in kwargs_keys})
    
    def setup(self):
        logging.info("Setting up beat handler")
    
    def loop(self):
        pass

    def close(self):
        logging.info("Closing beat handler")

    def handle_beat(self):
        pass
    
    def handle_onset(self):
        pass
    
    def handle_bpm(self, bpm):
        pass

    def run(self):
        log_format = "%(asctime)s\t%(levelname)s\tHandler: %(message)s"
        logging.basicConfig(level=logging.INFO, filename="beatviewer.log", format=log_format)
        logging.info("Starting beat handler process with PID %d", self.pid)
        self.setup()
        logging.info("Done setting up beat handler")
        try:
            while self.running:
                if self.pipe.poll():
                    event_flag, event_frame, event_time, event_value = self.pipe.recv()
                    if event_flag == BeatTrackerProcess.FLAG_BEAT:
                        self.handle_beat()
                    elif event_flag == BeatTrackerProcess.FLAG_ONSET:
                        self.handle_onset()
                    elif event_flag == BeatTrackerProcess.FLAG_BPM:
                        self.handle_bpm(event_value)
                self.loop()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.close()
        logging.info("Beat handler process has finished")
