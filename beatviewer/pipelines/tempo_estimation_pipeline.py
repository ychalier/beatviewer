import logging

import numpy
import scipy.signal
import scipy.fftpack


def create_pulse_trains(t_min, t_max):
    pulse_trains = {}
    for candidate_tempo in range(t_min, t_max + 1):
        for phi in range(candidate_tempo):
            pulse_trains[candidate_tempo, phi] = {}
            for pulse_index, pulse_weight in zip([1, 1.5, 2], [1, .5, .5]):
                for beat_index in [0, 1, 2, 3]:
                    i = int(phi + pulse_index * beat_index * candidate_tempo)
                    pulse_trains[candidate_tempo, phi].setdefault(i, 0)
                    pulse_trains[candidate_tempo, phi][i] += pulse_weight
    return pulse_trains


class TempoEstimationPipepline:

    def __init__(self, oss_sampling_rate, config):
        logging.info("Creating tempo estimation pipeline")
        self.oss_sampling_rate = oss_sampling_rate
        self.config = config
        self.t_min = None
        self.t_max = None
        self.oss_buffer = None
        self.oss_buffer_size = None
        self.eac = None
        self.pulse_trains = None
        self.instant_tempo_lag = None
        self.accumulator = None
        self.accumulated_tempo_lag = None
        self.scaled_tempo_lag = None

    def setup(self):
        logging.info("Setting up tempo estimation pipeline")
        self.t_min = int(60 * self.oss_sampling_rate / self.config.max_bpm_detection)
        self.t_max = int(60 * self.oss_sampling_rate / self.config.min_bpm_detection)
        self.oss_buffer = []
        self.oss_buffer_size = 0
        self.pulse_trains = create_pulse_trains(self.t_min, self.t_max)
        self.accumulator = numpy.zeros(self.t_max - self.t_min + 1)

    def enqueue_oss(self, oss):
        """Enqueue an OSS to the tempo estimator window. If the window reaches
        the size specified in config.oss_window_size, it triggers an update and
        returns True. Otherwise it returns False.
        """
        self.oss_buffer.append(oss)
        self.oss_buffer_size += 1
        if self.oss_buffer_size == self.config.oss_window_size:
            self.update()
            del self.oss_buffer[:self.config.oss_hop_size]
            self.oss_buffer_size -= self.config.oss_hop_size
            return True
        return False
    
    def update(self):
        logging.debug("Updating tempo estimation pipeline")
        self.update_eac()
        self.update_instant_tempo_lag()
        self.update_accumulator()

    def update_eac(self):
        corr = numpy.abs(scipy.fftpack.ifft(numpy.power(
            numpy.abs(scipy.fftpack.fft(self.oss_buffer)),
            self.config.frequency_domain_compression)))
        self.eac = numpy.copy(corr)
        for t in range(self.config.oss_window_size // 4):
            self.eac[t] += corr[2 * t] + corr[4 * t]
        for t in range(self.config.oss_window_size // 4, self.config.oss_window_size // 2):
            self.eac[t] += corr[2 * t]
    
    def update_instant_tempo_lag(self):
        peaks = scipy.signal.find_peaks(self.eac[self.t_min:self.t_max + 1])[0] + self.t_min
        if len(peaks) == 0:
            return
        tempo_candidates = min(len(peaks), self.config.tempo_candidates)
        top_peaks = numpy.argpartition(self.eac[peaks], -tempo_candidates)[-tempo_candidates:]
        scores_variance = numpy.zeros(tempo_candidates)
        scores_variance_sum = 0
        scores_maximum = numpy.zeros(tempo_candidates)
        scores_maximum_sum = 0
        for j, candidate_tempo in enumerate(peaks[top_peaks]):
            pulse_train_correlation = numpy.zeros(candidate_tempo)
            for phi in range(candidate_tempo):
                for i, v in self.pulse_trains[candidate_tempo, phi].items():
                    if i >= self.config.oss_window_size:
                        continue
                    pulse_train_correlation[phi] += v * self.oss_buffer[i]
            variance = numpy.var(pulse_train_correlation)
            scores_variance[j] = variance
            scores_variance_sum += variance
            maximum = numpy.max(pulse_train_correlation)
            scores_maximum[j] = maximum
            scores_maximum_sum += maximum
        if scores_variance_sum == 0:
            scores_variance_sum = 1
        if scores_maximum_sum == 0:
            scores_maximum_sum = 1
        scores = scores_variance / scores_variance_sum + scores_maximum / scores_maximum_sum
        j_max = numpy.argmax(scores)
        self.instant_tempo_lag = peaks[top_peaks][j_max]
    
    def update_accumulator(self):
        if self.instant_tempo_lag is None:
            return
        t = list(range(self.t_min, self.t_max + 1))
        self.accumulator *= self.config.tempo_accumulator_decay
        s = self.config.tempo_accumulator_gaussian_width
        self.accumulator += 1 / (s * numpy.sqrt(2 * numpy.pi)) * numpy.exp(-.5 * numpy.power((t - self.instant_tempo_lag) / s, 2))
        self.accumulated_tempo_lag = numpy.argmax(self.accumulator) + self.t_min
        bpm = 60 * self.oss_sampling_rate / self.accumulated_tempo_lag
        while bpm <= self.config.min_bpm_rescaled:
            bpm *= 2
        while bpm >= self.config.max_bpm_rescaled:
            bpm *= .5
        self.scaled_tempo_lag = 60 * self.oss_sampling_rate / bpm