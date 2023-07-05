import logging

import numpy


def create_hamming_window(size, a0=25/46):
    arr = numpy.zeros(size)
    for k in range(size):
        arr[k] = a0 - (1 - a0) * numpy.cos(2 * numpy.pi * k / size)
    return arr


class BeatTrackingPipeline:

    MODE_REGULAR = 0
    MODE_TEMPO_LOCKED = 1

    def __init__(self, config):
        logging.info("Creating beat tracking pipeline")
        self.config = config
        self.mode = self.MODE_REGULAR
        self.flux_buffer = None
        self.oss_buffer = None
        self.oss_buffer_size = 0
        self.oss_mean = 0
        self.oss_threshold = 0
        self.was_below_threshold = False
        self.hamming_window = None
        self.tempo_lag = 100
        self.phi_max = 0
        self.cbss_buffer = None
        self.bps_buffer = None
        self.beat_cooldown = 0
        self.running = True
        self.beat_flag = False
        self.onset_flag = False
        self.frame_index = -1

    def setup(self):
        """Instantiate object attributes.
        """
        logging.info("Setting up beat tracking pipeline")
        self.flux_buffer = numpy.zeros((self.config.hamming_window_size))
        self.oss_buffer = []
        self.oss_buffer_size = 0
        self.hamming_window = create_hamming_window(self.config.hamming_window_size)
        self.cbss_buffer = [0] * self.config.cbss_buffer_size
        self.bps_buffer = [0] * self.config.bps_buffer_size

    def enqueue_flux(self, flux):
        logging.debug("Enqueuing flux value %f", flux)
        self.frame_index += 1
        self.flux_buffer[:self.config.hamming_window_size - 1] = self.flux_buffer[1:]
        self.flux_buffer[-1] = flux
        self.update_oss()
        self.update_cbss()
        self.update_phi_max()
        self.update_bps()
        self.update_beat()

    def set_tempo_lag(self, tempo_lag):
        """Set the tempo_lag attribute
        """
        if self.mode != self.MODE_TEMPO_LOCKED:
            self.tempo_lag = tempo_lag

    def update_oss(self):
        """Compute the next OSS value and store it into a buffer.
        Return whether there was an onset.
        """
        oss = numpy.sum(numpy.multiply(self.flux_buffer, self.hamming_window))
        if self.oss_buffer_size == max(self.config.oss_window_size, self.config.oss_buffer_size):
            self.oss_buffer.pop(0)
            self.oss_buffer_size -= 1
        self.oss_buffer.append(oss)
        self.oss_buffer_size += 1
        self.oss_mean = numpy.mean(self.oss_buffer[-self.config.oss_buffer_size:])
        oss_std = numpy.sqrt(numpy.var(self.oss_buffer[-self.config.oss_buffer_size:]))
        self.oss_threshold = max(
            self.oss_mean + self.config.onset_threshold * oss_std,
            self.config.onset_threshold_min
        )
        self.onset_flag = False
        if oss < self.oss_threshold:
            self.was_below_threshold = True
            logging.debug("Detected onset")
        elif self.was_below_threshold:
            self.was_below_threshold = False
            self.onset_flag = True
        return self.onset_flag

    def update_cbss(self):
        """Compute the next CBSS value and store it into a buffer.
        """
        self.cbss_buffer.pop(0)
        self.cbss_buffer.append(0)
        n = self.config.cbss_buffer_size - 1
        phi = 0
        for v in range(-2 * self.tempo_lag, -self.tempo_lag // 2):
            if n + v < 0:
                continue
            gaussian_weight = numpy.exp(-.5 * (self.config.cbss_eta * numpy.power(numpy.log(-v/self.tempo_lag), 2)))
            phi = max(phi, gaussian_weight * self.cbss_buffer[n + v])
        if self.mode == self.MODE_TEMPO_LOCKED:
            self.cbss_buffer[n] = phi
        else:
            self.cbss_buffer[n] = (1 - self.config.cbss_alpha) * self.oss_buffer[-1] + self.config.cbss_alpha * phi
    
    def update_phi_max(self):
        """Compute the phase estimation.
        """
        phi_max, phi_max_value = None, None
        n = self.config.cbss_buffer_size - 1
        for phi in range(self.tempo_lag):
            phi_value = 0
            for i in range(4):
                if n - phi - i * self.tempo_lag < 0:
                    continue
                phi_value += self.cbss_buffer[n - phi - i * self.tempo_lag]
            if phi_max is None or phi_value > phi_max_value:
                phi_max, phi_max_value = phi, phi_value
        self.phi_max = phi_max

    def update_bps(self):
        """Update the BPS buffer.
        """
        self.bps_buffer.pop(0)
        self.bps_buffer.append(0)
        epsilon = self.config.bps_epsilon_o + self.config.bps_epsilon_r
        tt = [
            (i % self.tempo_lag) - (self.tempo_lag - self.phi_max - epsilon)
            for i in range(self.config.bps_buffer_size)
        ]
        pmi = numpy.exp(-numpy.power(tt, 2) / self.config.bps_gaussian_width)
        for i in range(self.config.bps_buffer_size):
            self.bps_buffer[i] += pmi[i]
        
    def update_beat(self):
        """Take the decision of the presence of a beat.
        """
        self.beat_flag = False
        if self.beat_cooldown > 0:
            self.beat_cooldown -= 1
            return False
        self.beat_flag = self.bps_buffer[self.config.bps_epsilon_t] == max(self.bps_buffer)        
        if self.beat_flag:
            self.beat_cooldown = int(self.config.bps_cooldown_ratio * self.tempo_lag)
            logging.debug("Detected beat")
        return self.beat_flag