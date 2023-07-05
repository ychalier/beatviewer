class Config:

    def __init__(
        self,
        audio_window_size=1024,
        audio_hop_size=128,
        compression_gamma=1,
        noise_cancellation_level=-74,
        hamming_window_size=15,
        oss_buffer_size=1024,
        onset_threshold=0.1,
        onset_threshold_min=5.0,
        oss_window_size=2048,
        oss_hop_size=128,
        frequency_domain_compression=.5,
        min_bpm_detection=50,
        max_bpm_detection=210,
        tempo_candidates=10,
        tempo_accumulator_decay=.9,
        tempo_accumulator_gaussian_width=10,
        min_bpm_rescaled=90,
        max_bpm_rescaled=180,
        cbss_eta=300,
        cbss_alpha=0.9,
        bps_buffer_size=1024,
        bps_epsilon_o=0,
        bps_epsilon_r=0,
        bps_epsilon_t=20,
        bps_gaussian_width=10,
        cbss_buffer_size=512,
        bps_cooldown_ratio=0.4,
        key_trigger_beats_earlier="page up",
        key_trigger_beats_later="page down",
        key_set_mode_regular="f9",
        key_set_mode_tempo_locked="f10",
    ):

        # OSS Computation
        self.audio_window_size = audio_window_size
        self.audio_hop_size = audio_hop_size
        self.compression_gamma = compression_gamma
        self.noise_cancellation_threshold = 10 ** (noise_cancellation_level / 20) * self.audio_window_size
        self.hamming_window_size = hamming_window_size

        # Onset Detection
        self.oss_buffer_size = oss_buffer_size
        self.onset_threshold = onset_threshold
        self.onset_threshold_min = onset_threshold_min

        # Tempo Detection
        self.oss_window_size = oss_window_size
        self.oss_hop_size = oss_hop_size
        self.frequency_domain_compression = frequency_domain_compression
        self.min_bpm_detection = min_bpm_detection
        self.max_bpm_detection = max_bpm_detection
        self.tempo_candidates = tempo_candidates
        self.tempo_accumulator_decay = tempo_accumulator_decay
        self.tempo_accumulator_gaussian_width = tempo_accumulator_gaussian_width
        self.min_bpm_rescaled = min_bpm_rescaled
        self.max_bpm_rescaled = max_bpm_rescaled

        # CBSS Computation
        self.cbss_buffer_size = cbss_buffer_size
        self.cbss_eta = cbss_eta
        self.cbss_alpha = cbss_alpha

        # BPS Computation
        self.bps_epsilon_o = bps_epsilon_o
        self.bps_epsilon_r = bps_epsilon_r
        self.bps_epsilon_t = bps_epsilon_t
        self.bps_gaussian_width = bps_gaussian_width
        self.bps_buffer_size = bps_buffer_size
        self.bps_cooldown_ratio = bps_cooldown_ratio

        # Keys
        self.key_trigger_beats_earlier = key_trigger_beats_earlier
        self.key_trigger_beats_later = key_trigger_beats_later
        self.key_set_mode_regular = key_set_mode_regular
        self.key_set_mode_tempo_locked = key_set_mode_tempo_locked
    
    @classmethod
    def from_file(cls, path):
        kwargs = {}
        with open(path, "r", encoding="utf8") as file:
            for line in file.readlines():
                lstrip = line.strip()
                if lstrip == "":
                    continue
                if lstrip.startswith("#"):
                    continue
                argname, *argvals = lstrip.split()
                argval = " ".join(argvals)
                try:
                    kwargs[argname] = int(argval)
                except ValueError:
                    try:
                        kwargs[argname] = float(argval)
                    except ValueError:
                        kwargs[argname] = str(argval)
        return cls(**kwargs)
    
    def update(self, key, value):
        setattr(self, key, value)