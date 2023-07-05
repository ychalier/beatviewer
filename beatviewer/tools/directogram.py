import json
import math
import os

import cv2
import numpy
import tqdm

from ..video.video_reader import VideoReader
from .tool import Tool


class Directogram(Tool, VideoReader):

    NAME = "directogram"

    def __init__(self, path, deadzone=0.05, bins=128, average_period=1, maximum_period=.15, sigma=2, skip_directogram=False):
        Tool.__init__(self)
        VideoReader.__init__(self, path)
        self.last_frame = None
        self.next_frame = None
        self.directogram = []
        self.checkpoints = []
        self.deadzone = deadzone
        self.bins = bins
        self.average_period = average_period
        self.maximum_period = maximum_period
        self.sigma = sigma
        self.skip_directogram = skip_directogram
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("path", type=str, help="Path to the video file")
        parser.add_argument("-s", "--skip-directogram", action="store_true", help="Set this flag to skip directogram computation, and reuse saved data")
        parser.add_argument("--average-period", type=float, default=1.0, help="Length in seconds of the window for computating signal average and standard deviation")
        parser.add_argument("--maximum-period", type=float, default=0.15, help="Length in seconds of the window for computatig signal local maxima")
        parser.add_argument("--sigma", type=float, default=2.0, help="Threshold to detect a checkpoint, as a number of std above the mean")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["path"], ["skip_directogram", "average_period", "maximum_period", "sigma"])
    
    def save(self):
        path = os.path.splitext(self.path)[0] + ".json"
        with open(path, "w") as file:
            json.dump({
                "path": self.path,
                "frame_count": self.frame_count,
                "frame_rate": self.fps,
                "width": self.width,
                "height": self.height,
                "checkpoints": sorted(self.checkpoints),
                "directogram": self.directogram.tolist()
            }, file)
    
    def load(self):
        path = os.path.splitext(self.path)[0] + ".json"
        if not os.path.isfile(path):
            return
        with open(path, "r") as file:
            data = json.load(file)
        self.checkpoints = data.get("checkpoints")
        self.directogram = numpy.array(data["directogram"]) if "directogram" in data else None

    def increment_cursor(self):
        self.last_frame = self.next_frame
        self.next_frame = numpy.mean(self.read_frame(), axis=2)

    def compute_optical_flow(self):
        flow = cv2.calcOpticalFlowFarneback(
            prev=self.last_frame,
            next=self.next_frame,
            flow=None,
            pyr_scale=0.5,
            levels=int(math.log(float(min(self.next_frame.shape)), 2)) - 4,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.25,
            flags=0,
        )
        flow_angle = numpy.arctan2(flow[:,:,1], flow[:,:,0]) + numpy.pi
        flow_radius = numpy.sqrt(numpy.sum(numpy.power(flow, 2), axis=2))
        starty = int(self.deadzone * self.next_frame.shape[0])
        endy = self.next_frame.shape[0] - starty
        startx = int(self.deadzone * self.next_frame.shape[1])
        endx = self.next_frame.shape[1] - startx
        return flow_angle[starty:endy, startx:endx], flow_radius[starty:endy, startx:endx]
    
    def compute_directogram(self):
        self.cursor = 0
        self.next_frame = numpy.mean(self.read_frame(), axis=2)
        histograms = []
        for _ in tqdm.tqdm(range(1, self.frame_count), unit="frame"):
            self.increment_cursor()
            flow_angle, flow_radius = self.compute_optical_flow()
            histogram, _ = numpy.histogram(
                flow_angle.ravel(),
                bins=self.bins,
                range=(0, 2 * numpy.pi),
                weights=flow_radius.ravel(),
                density=None
            )
            histograms.append(histogram)
        self.directogram = numpy.array(histograms)
        # TODO: apply 3x3 median filter
        return self.directogram
    
    def extract_checkpoints(self):
        flux = numpy.sum(
            numpy.maximum(0, self.directogram[1:,:] - self.directogram[:-1,:]),
            axis=1)
        flux /= numpy.max(flux)
        local_mean_width = int(self.average_period * self.fps)
        local_maxima_width = int(self.maximum_period * self.fps)
        self.checkpoints = []
        for i in range(flux.shape[0]):
            window = flux[max(0, int(i - local_mean_width / 2)):min(flux.shape[0], int(i + local_mean_width / 2) + 1)]
            mean = numpy.mean(window)
            std = numpy.sqrt(numpy.var(window))
            local_maximum = max(flux[
                max(0, int(i - local_maxima_width / 2)):
                min(int(i + local_maxima_width / 2) + 1, flux.shape[0])])
            if flux[i] == local_maximum and flux[i] > mean + self.sigma * std:
                self.checkpoints.append(i + 2)
        return self.checkpoints

    def run(self):
        self.open()
        self.load()
        if not self.skip_directogram:
            self.compute_directogram()
        self.extract_checkpoints()
        self.save()
