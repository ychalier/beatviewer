import logging
import time

import soundfile
import tqdm

from .audio_source import AudioSource


class FileAudioSource(AudioSource):
    """Load audio frames from a local file. A progress bar indicates the
    progression within the file. Only support int16 WAVE files. Multichannel
    signals are averaged to a mono signal. 
    """

    def __init__(self, config, path, realtime=False, record_path=None):
        logging.info(
            "Creating file audio source from '%s', realtime is %s",
            path,
            realtime
        )
        self.path = path
        self.realtime = realtime
        data, sr = soundfile.read(self.path, dtype="int16", start=0)
        AudioSource.__init__(self, config, int(sr), record_path=record_path)
        self.data = data
        self.i = 0
        self.last_window_update = 0
        self.window_update_period = self.config.audio_hop_size / sr
        self.pbar = None
    
    def setup(self):
        AudioSource.setup(self)
        self.pbar = tqdm.tqdm(
            total=len(self.data),
            unit="sample",
            unit_scale=True
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
                window[k + j] = int(sum(self.data[self.i]) / self.data.shape[1])
            self.i += 1
            self.pbar.update()
    
    def close(self):
        self.pbar.close()