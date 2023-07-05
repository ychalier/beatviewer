import logging
import threading
import warnings

import matplotlib.animation
import matplotlib.pyplot
import numpy


class Graph(threading.Thread):
    """A graph plotting realtime data from a beat tracker. Plots OSS and CBSS
    signals, BPS predicted signal, shows BPM and estimated phase. Everything
    is packed in a thread to be concurrent to original computation.
    """

    def __init__(self, beat_tracker, visualizer_size, fps):
        threading.Thread.__init__(self, daemon=True)
        self.tracker = beat_tracker
        self.size = visualizer_size
        self.fps = fps
        self.figure = None
        self.axis = None
        self.plot_oss = None
        self.plot_oss_mean = None
        self.plot_oss_threshold = None
        self.plot_cbss = None
        self.plot_bps = None
        self.plot_detection_length = None
        self.plot_beat_trigger_index = None
        self.text_bpm = None
        self.animation = None

    def run(self):
        logging.info("Starting graph thread with ID %d", threading.get_ident())

        warnings.filterwarnings("ignore")
        figure, axis = matplotlib.pyplot.subplots(1, 1)
        self.figure = figure

        # Force the user to use ^C to close the program
        self.figure.canvas.manager.window.overrideredirect(1)

        self.axis = axis
        self.axis.set_xlim(0, 2 * self.size - 1)
        self.axis.set_ylim(0, 1.1)
        xticks = range(0, 2 * self.size, 2 ** (round(numpy.log2(self.size)) - 2))
        self.axis.set_xticks(xticks)
        self.axis.set_xticklabels(["%.1fs" % ((x - self.size) / self.tracker.sampling_rate_oss) for x in xticks])
        self.axis.spines["top"].set_visible(False)
        self.axis.spines["right"].set_visible(False)
        self.axis.spines["left"].set_visible(False)
        self.axis.axes.get_yaxis().set_visible(False)

        self.plot_oss = self.axis.plot([0] * self.size, label="OSS")[0]
        self.plot_oss_mean = self.axis.plot([0, self.size - 1], [self.tracker.oss_mean, self.tracker.oss_mean], "-", label="OSS mean")[0]
        self.plot_oss_threshold = self.axis.plot([0, self.size - 1], [self.tracker.oss_threshold, self.tracker.oss_threshold], "-", label="OSS threshold")[0]
        self.plot_cbss = self.axis.plot(self.tracker.cbss_buffer[-self.size:], label="CBSS")[0]
        self.plot_bps = self.axis.plot(range(self.size, 2 * self.size), self.tracker.cbss_buffer[-self.size:], "--", label="BPS")[0]
        self.plot_detection_length = self.axis.plot([0, 0], [0, 0], label="Δt")[0]
        self.plot_beat_trigger_index = self.axis.plot([self.size + self.tracker.config.bps_epsilon_t, self.size + self.tracker.config.bps_epsilon_t], [0, 1], label="εt")[0]
        self.text_bpm = self.axis.text(self.size, 1.03, "%.2f" % (60 * self.tracker.sampling_rate_oss / self.tracker.tempo_lag), ha="center")
        
        self.axis.legend(loc="upper right")

        def update(frame, *fargs):
            max_oss = .1
            if len(self.tracker.oss_buffer[-self.size:]):
                max_oss = max(self.tracker.oss_buffer[-self.size:])
            vmax_l = max(
                .1,
                max_oss,
                max(self.tracker.cbss_buffer[-self.size:])
            )
            vmax_r = max(
                .1,
                max(self.tracker.bps_buffer[:self.size])
            )
            oss_values = self.tracker.oss_buffer[-self.size:]
            if len(oss_values) < self.size:
                oss_values = [0] * (self.size - len(oss_values)) + oss_values
            self.plot_oss.set_ydata(list(map(lambda y: y / vmax_l, oss_values)))
            self.plot_oss_mean.set_ydata([self.tracker.oss_mean / vmax_l, self.tracker.oss_mean / vmax_l])
            self.plot_oss_threshold.set_ydata([self.tracker.oss_threshold / vmax_l, self.tracker.oss_threshold / vmax_l])
            self.plot_cbss.set_ydata(list(map(lambda y: y / vmax_l, self.tracker.cbss_buffer[-self.size:])))
            self.plot_bps.set_ydata(list(map(lambda y: y / vmax_r, self.tracker.bps_buffer[:self.size])))
            self.plot_detection_length.set_data([self.size - self.tracker.phi_max - self.tracker.tempo_lag, self.size - self.tracker.phi_max], [self.tracker.cbss_buffer[-self.tracker.phi_max] / vmax_l, self.tracker.cbss_buffer[-self.tracker.phi_max] / vmax_l])
            self.text_bpm.set_text("%.2f" % (60 * self.tracker.sampling_rate_oss / self.tracker.tempo_lag))
            self.plot_beat_trigger_index.set_xdata([self.size + self.tracker.config.bps_epsilon_t, self.size + self.tracker.config.bps_epsilon_t])
            return self.plot_oss, self.plot_cbss, self.plot_bps, self.plot_oss_mean, self.plot_oss_threshold, self.plot_detection_length, self.plot_beat_trigger_index, self.text_bpm

        self.animation = matplotlib.animation.FuncAnimation(self.figure, update, blit=True, interval=round(1000 / self.fps))
        matplotlib.pyplot.show()
    
    def terminate(self):
        logging.info("Closing graph thread")
        # Matplotlib does not behave well when not in the main thread.
        # This hacks helps for it to close nicely.
        root = self.figure.canvas.manager.window._root()
        matplotlib.pyplot.close()
        root.quit()

    