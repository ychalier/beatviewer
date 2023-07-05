import logging
import time

import numpy
import sounddevice

from .audio_source import AudioSource


class LiveAudioSource(AudioSource):
    """Load audio frames from an audio input device. Multichannel signals are
    averaged to a mono signal.
    """

    def __init__(self, config, device_index, record_path=None):
        logging.info(
            "Creating live audio source for device index %d",
            device_index
        )
        self.device_index = device_index
        self.device_info = sounddevice.query_devices(self.device_index, "input")
        self.channels = int(self.device_info["max_input_channels"])
        self.stream = None
        self.overflow_ts = None
        self.stats_overflowing = 0
        self.stats_total = 0
        AudioSource.__init__(
            self,
            config, 
            int(self.device_info["default_samplerate"]), 
            record_path=record_path
        )

    def setup(self):
        logging.info("Setting up live audio source")
        AudioSource.setup(self)
        self.stream = sounddevice.InputStream(
            device=self.device_index,
            channels=self.channels,
            samplerate=self.sampling_rate,
            blocksize=self.config.audio_hop_size,
            dtype="int16"
        )
        self.stream.start()
    
    def _update_window(self, window):
        data, overflowed = self.stream.read(frames=self.config.audio_hop_size)
        if overflowed:
            self.stats_overflowing += 1
            if self.overflow_ts is None:
                self.overflow_ts = time.time()
        self.stats_total += 1
        if self.overflow_ts is not None and time.time() - self.overflow_ts > 1:
            logging.warning(
                "Audio stream lost %d chunks of %d (%.0f%%) in the last second",
                self.stats_overflowing,
                self.stats_total,
                100 * self.stats_overflowing / self.stats_total
            )
            self.overflow_ts = None
            self.stats_total = 0
            self.stats_overflowing = 0
        n = self.config.audio_window_size - self.config.audio_hop_size
        window[:n] = window[self.config.audio_hop_size:]
        window[n:] = (numpy.sum(data, axis=1) / data.shape[1]).astype("int16")
    
    def close(self):
        logging.info("Closing live audio source")
        AudioSource.close(self)
        self.stream.abort()