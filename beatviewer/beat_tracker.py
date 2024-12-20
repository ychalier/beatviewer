import dataclasses
import enum
import json
import logging
import math

import keyboard

from .graph import Graph
from .pipelines.pipeline import Pipeline


@enum.unique
class EventFlag(enum.Enum):
    ONSET = 0
    BEAT = 1
    BPM = 2

    @staticmethod
    def to_string(flag) -> str:
        if flag == EventFlag.ONSET:
            return "ONSET"
        elif flag == EventFlag.BEAT:
            return "BEAT"
        elif flag == EventFlag.BPM:
            return "BPM"
        else:
            return "OTHER"


@dataclasses.dataclass
class BeatTrackingEvent:

    flag: EventFlag
    frame: int
    time: int
    value: float | None

    def to_dict(self):
        return {
            "flag": EventFlag.to_string(self.flag),
            "frame": self.frame,
            "time": self.time,
            "value": self.value
        }


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
        graph_fps=15,
        keyboard_events=False,
        output_path=None,
        register_events: bool = False,
        warmup: bool = False,
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
        self.graph_interval = 1
        self.keybord_events = keyboard_events
        self.sampling_rate = None
        self.sampling_rate_oss = None
        self.output_path = output_path
        self.register_events = register_events or (self.output_path is not None)
        self.warmup: bool = warmup
        self.rewound: bool = False
        self.events: list[BeatTrackingEvent] = []
    
    def register_event(self, flag: EventFlag, value: float | None = None):
        if not self.register_events:
            return
        self.events.append(BeatTrackingEvent(
            flag,
            self.frame_index,
            self.frame_index / self.sampling_rate_oss,
            value
        ))
        
    def setup(self):
        logging.info("Setting up beat tracker")
        Pipeline.setup(self)
        self.sampling_rate = self.audio_source.sampling_rate
        self.sampling_rate_oss = self.sampling_rate / self.config.audio_hop_size
        self.graph_interval = math.ceil(self.sampling_rate_oss / self.graph_fps)
        if self.show_graph:
            self.graph = Graph(self, self.graph_size)
            self.graph.start()

    def close(self):
        logging.info("Closing beat tracker")
        if self.show_graph:
            self.graph.terminate()
        if self.output_path is not None:
            data = {
                "sampling_rate_oss": self.sampling_rate_oss,
                "config": self.config.to_dict(),
                "events": [event.to_dict() for event in self.events]
            }
            with open(self.output_path, "w") as file:
                json.dump(data, file)
    
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
        if self.graph is not None and self.frame_index % self.graph_interval == 0:
            self.graph.update()

    def handle_onset(self):
        self.register_event(EventFlag.ONSET)
        if self.onset_callback is not None:
            self.onset_callback()
    
    def handle_beat(self):
        self.register_event(EventFlag.BEAT)
        if self.beat_callback is not None:
            self.beat_callback()
    
    def handle_bpm(self):
        self.register_event(EventFlag.BPM, self.bpm)
        if self.bpm_callback is not None:
            self.bpm_callback(self.bpm)
    
    def rewind(self):
        Pipeline.rewind(self)
        self.events = []
        self.rewound = True
    
    def run(self):
        self.setup()
        logging.info("Done setting up beat tracker")
        i = 0
        while self.running and self.active:
            if self.warmup and self.warmup_end is not None and self.frame_index >= self.warmup_end and not self.rewound:
                self.rewind()
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