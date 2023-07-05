import logging

import cv2
import numpy


class VideoReader:

    def __init__(self, path):
        self.path = path
        self.capture = None
        self.cursor = None
        self.width = None
        self.height = None
        self.fps = None
        self.frame_count = None

    def open(self):
        logging.info("Opening video capture for path %s", self.path)
        self.capture = cv2.VideoCapture(self.path)
        self.cursor = 0
        self.initialize_properties()

    def compute_frame_count(self, margin=5):
        frame_count_estimate = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count_estimate - margin)
        frame_count = frame_count_estimate - margin
        while True:
            success, _ = self.capture.read()
            if success:
                frame_count += 1
            else:
                break
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, self.cursor)
        self.frame_count = frame_count

    def initialize_properties(self):
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.compute_frame_count()
        logging.info("Video properties: %dx%d, %d frames, %.2f FPS", self.width, self.height, self.frame_count, self.fps)

    def read_frame(self, i=None):
        if i is None:
            i = self.cursor
        while i < 0:
            i += self.frame_count        
        i = i % self.frame_count
        if i != self.cursor:
            self.cursor = i
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, self.cursor)
        success, frame = self.capture.read()
        if success:
            self.cursor += 1
        else:
            logging.error("Could not read video frame %d", self.cursor)
        return frame
    
    @staticmethod
    def convert_frame(frame, scale=None, transpose=True):
        f = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if scale is not None:
            f = cv2.resize(f, scale)
        if transpose:
            return numpy.transpose(f, axes=(1, 0, 2))
        return f

    def close(self):
        self.capture.release()