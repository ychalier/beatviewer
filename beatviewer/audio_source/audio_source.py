import logging
import wave


class AudioSource:
    """Interface for audio source signal. It wraps utilities for updating an
    array of audio samples and recording them to a local file.
    """

    def __init__(self, config, sampling_rate, record_path=None):
        logging.info(
            "Creating audio source, with sampling rate %d Hz",
            sampling_rate
        )
        self.config = config
        self.sampling_rate = sampling_rate
        self.record_path = record_path
        self.record_file = None
        self.active = True

    def setup(self):
        logging.info("Setting up audio source")
        if self.record_path is not None:
            self.record_file = wave.open(self.record_path, "wb")
            self.record_file.setnchannels(1)
            self.record_file.setsampwidth(2)
            self.record_file.setframerate(self.sampling_rate)

    def _update_window(self, window):
        raise NotImplementedError
    
    def update_window(self, window):
        logging.debug("Updating audio source window")
        self._update_window(window)
        if self.record_file is not None:
            i = self.config.audio_window_size - self.config.audio_hop_size
            self.record_file.writeframes(window[i:].astype("<h").tobytes())
    
    def close(self):
        logging.info("Closing audio source")
        if self.record_path is not None:
            self.record_file.close()