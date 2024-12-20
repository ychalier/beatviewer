import logging
import time

import numpy
import soundfile
import tqdm

from .audio_source import AudioSource


class FileAudioSource(AudioSource):
    """Load audio frames from a local file. A progress bar indicates the
    progression within the file. Only support int16 WAVE files. Multichannel
    signals are averaged to a mono signal. 
    """

    def __init__(self, config, path, realtime=False, record_path=None,
                 pbar_kwargs=None):
        logging.info(
            "Creating file audio source from '%s', realtime is %s",
            path,
            realtime
        )
        self.path = path
        self.realtime = realtime
        data, sr = soundfile.read(self.path, dtype="int16", start=0)
        AudioSource.__init__(self, config, int(sr), record_path=record_path)
        if data.shape[1] == 1:
            self.data = data
        else:
            self.data = numpy.sum(data.astype("int32"), axis=1) / data.shape[1]
        self.i = 0
        self.last_window_update = 0
        self.window_update_period = self.config.audio_hop_size / sr
        self.pbar = None
        self.pbar_kwargs = {} if pbar_kwargs is None else pbar_kwargs
        self.length = len(self.data)
    
    def setup(self):
        AudioSource.setup(self)
        self.pbar = tqdm.tqdm(
            total=len(self.data),
            unit="sample",
            unit_scale=True,
            **self.pbar_kwargs
        )

    def _update_window(self, window):
        if self.realtime:
            while True:
                now = time.time()
                if now - self.last_window_update >= self.window_update_period:
                    self.last_window_update = now
                    break
                pass
        if self.i >= self.data.shape[0]:
            self.active = False
            logging.info("Reached end of audio file source")
            return
        k = self.config.audio_window_size - self.config.audio_hop_size
        window[:k] = window[self.config.audio_hop_size:]
        for j in range(self.config.audio_hop_size):
            if self.i >= self.data.shape[0]:
                window[k + j] = 0
            else:
                window[k + j] = self.data[self.i]
            self.i += 1
        self.pbar.update(min(self.config.audio_hop_size, self.length - self.pbar.n))
    
    def close(self):
        self.pbar.close()