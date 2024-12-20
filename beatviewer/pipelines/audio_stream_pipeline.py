import logging

import numpy
import scipy.fftpack


class AudioStreamPipeline:

    def __init__(self, config, audio_source):
        logging.info("Creating audio stream pipeline")
        self.config = config
        self.audio_source = audio_source
        self.sampling_rate = audio_source.sampling_rate
        self.audio_window = None 
        self.previous_fft = None
        self.flux = None
    
    def setup(self):
        logging.info("Setting up audio stream pipeline")
        self.audio_source.setup()
        self.audio_window = numpy.zeros(self.config.audio_window_size)
        self.previous_fft = numpy.zeros(self.config.audio_window_size)

    def update(self):
        logging.debug("Updating audio stream pipeline")
        self.audio_source.update_window(self.audio_window)
        fft = numpy.abs(scipy.fftpack.fft(self.audio_window)) / self.sampling_rate
        g = self.config.compression_gamma
        if g != 0:
            fft = numpy.log10(1 + g * fft) / numpy.log10(1 + g)
        fft[fft < self.config.noise_cancellation_threshold] = 0
        self.flux = numpy.sum(numpy.maximum(fft - self.previous_fft, 0))
        self.previous_fft = fft

    def close(self):
        logging.info("Closing audio stream pipeline")
        self.audio_source.close()
    
    def rewind(self):
        logging.info("Rewinding audio stream pipeline")
        self.audio_source.rewind()