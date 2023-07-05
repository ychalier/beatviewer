import logging

import keyboard

from .graph import Graph
from .pipelines.pipeline import Pipeline


class BeatTracker(Pipeline):

    def __init__(
        self,
        config,
        audio_source,
        onset_callback=None,
        beat_callback=None,
        bpm_callback=None,
        show_graph=False,
        graph_size=512,
        graph_fps=30,
        keyboard_events=False,
        output_path=None
    ):
        logging.info("Creating beat tracker")
        Pipeline.__init__(self, config, audio_source)
        self.onset_callback = onset_callback
        self.beat_callback = beat_callback
        self.bpm_callback = bpm_callback
        self.show_graph = show_graph
        self.graph = None
        self.graph_size = graph_size
        self.graph_fps = graph_fps
        self.keybord_events = keyboard_events
        self.sampling_rate = None
        self.sampling_rate_oss = None
        self.output_path = output_path
        self.output_file = None
        
    def setup(self):
        logging.info("Setting up beat tracker")
        Pipeline.setup(self)
        self.sampling_rate = self.audio_source.sampling_rate
        self.sampling_rate_oss = self.sampling_rate / self.config.audio_hop_size
        if self.show_graph:
            self.graph = Graph(self, self.graph_size, self.graph_fps)
            self.graph.start()
        if self.output_path is not None:
            self.output_file = open(self.output_path, "w")
            self.output_file.write("event_flag\tevent_frame\tevent_time\tevent_value\n")
            self.output_file.write("SAMPLING_RATE_OSS\t0\t0\t%f\n" % self.sampling_rate_oss)
            
    def close(self):
        logging.info("Closing beat tracker")
        if self.show_graph:
            self.graph.terminate()
        if self.show_graph:
            self.graph.join()
        if self.output_path is not None:
            self.output_file.close()
    
    def check_keyboard_events(self):
        if keyboard.is_pressed(self.config.key_trigger_beats_earlier):
            if self.config.bps_epsilon_t < self.config.bps_buffer_size - 1:
                self.config.bps_epsilon_t += 1
                print("Triggering beats earlier (%d)" % self.config.bps_epsilon_t)
        elif keyboard.is_pressed(self.config.key_trigger_beats_later):
            if self.config.bps_epsilon_t > 0:
                self.config.bps_epsilon_t -= 1
                print("Triggering beats later (%d)" % self.config.bps_epsilon_t)
        elif keyboard.is_pressed(self.config.key_set_mode_regular):
            self.mode = self.MODE_REGULAR
            print("Changing mode to REGULAR")
        elif keyboard.is_pressed(self.config.key_set_mode_tempo_locked):
            self.mode = self.MODE_TEMPO_LOCKED
            print("Changing mode to TEMPO_LOCKED")

    def update(self):
        logging.debug("Updating beat tracker")
        Pipeline.update(self)
        if self.onset_flag:
            self.handle_onset()
        if self.beat_flag:
            self.handle_beat()
        if self.bpm_flag:
            self.handle_bpm()

    def write_output_line(self, key, value=None):
        if value is None:
            self.output_file.write("%s\t%d\t%.3f\t\n" % (
                key,
                self.frame_index,
                self.frame_index / self.sampling_rate_oss))
        else:
            self.output_file.write("%s\t%d\t%.3f\t%.2f\n" % (
                key,
                self.frame_index,
                self.frame_index / self.sampling_rate_oss,
                value))

    def handle_onset(self):
        if self.output_path is not None:
            self.write_output_line("ONSET")
        if self.onset_callback is not None:
            self.onset_callback()
    
    def handle_beat(self):
        if self.output_path is not None:
            self.write_output_line("BEAT")
        if self.beat_callback is not None:
            self.beat_callback()
    
    def handle_bpm(self):
        if self.output_path is not None:
            self.write_output_line("BPM", self.bpm)
        if self.bpm_callback is not None:
            self.bpm_callback(self.bpm)
    
    def run(self):
        self.setup()
        logging.info("Done setting up beat tracker")
        i = 0
        while self.running and self.active:
            i += 1
            try:
                if i == 10:
                    i = 0
                    if self.keybord_events:
                        self.check_keyboard_events()
                self.update()
            except KeyboardInterrupt:
                break
        self.close()