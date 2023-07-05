import logging

from .audio_stream_pipeline import AudioStreamPipeline
from .beat_tracking_pipeline import BeatTrackingPipeline
from .tempo_estimation_pipeline import TempoEstimationPipepline


class Pipeline(AudioStreamPipeline, BeatTrackingPipeline, TempoEstimationPipepline):

    def __init__(self, config, audio_source):
        logging.info("Creating pipeline")
        AudioStreamPipeline.__init__(self, config, audio_source)
        BeatTrackingPipeline.__init__(self, config)
        TempoEstimationPipepline.__init__(self, audio_source.sampling_rate / config.audio_hop_size, config)
        self.oss_buffer_counter = None
        self.bpm_flag = False
        self.active = True

    def setup(self):
        logging.info("Setting up pipeline")
        AudioStreamPipeline.setup(self)
        BeatTrackingPipeline.setup(self)
        TempoEstimationPipepline.setup(self)
        self.oss_buffer_counter = 0
    
    def update(self):
        logging.debug("Updating pipeline")
        AudioStreamPipeline.update(self)
        self.active = self.audio_source.active
        BeatTrackingPipeline.enqueue_flux(self, self.flux)
        self.oss_buffer_counter += 1
        self.bpm_flag = False
        if self.oss_buffer_counter >= self.config.oss_hop_size and self.oss_buffer_size == self.config.oss_window_size:
            self.oss_buffer_counter = 0
            TempoEstimationPipepline.update(self)
            if self.scaled_tempo_lag is None:
                return
            new_tempo_lag = int(self.scaled_tempo_lag)
            if new_tempo_lag != self.tempo_lag:
                self.tempo_lag = new_tempo_lag
                self.bpm_flag = True
                logging.debug("New tempo lag: %d", self.tempo_lag)

    def close(self):
        logging.info("Closing pipeline")
        AudioStreamPipeline.close(self)

    @property
    def bpm(self):
        return 60 * self.oss_sampling_rate / self.tempo_lag