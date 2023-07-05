"""
Inspiration: https://wifflegif.com/gifs/424480-monochrome-infinite-gif
"""

import math
import time

import pygame

from .pygame_handler import PygameHandler


BACKROUND = (225, 225, 228)
FOREGROUND = (0, 0, 0)


def gaussian(mu, sigma):
    return lambda t: math.exp(-.5 * ((t - mu) / sigma) ** 2)


class Waves(PygameHandler):

    NAME = "waves"

    def __init__(
            self,
            pipe,
            width=400,
            height=400,
            fullscreen=False,
            fps=60,
            line_count=20,
            line_offset=0.05,
            dot_count=50,
            dot_offset=0.01,
            sigma=0.1,
            amplitude=10,
            offset=0,
            abs_distance=False,
            buffer_size=20,
        ):
        PygameHandler.__init__(self, pipe, width, height, fullscreen, fps)
        self.line_count = line_count
        self.line_offset_seconds = line_offset
        self.dot_count = dot_count
        self.dot_offset_seconds = dot_offset
        self.gaussians_buffer_size = buffer_size
        self.gaussian_sigma = sigma
        self.gaussian_amplitude = amplitude
        self.gaussian_offset_seconds = offset
        self.abs_distance = abs_distance
        self.gaussians = []
        self.t0 = None

    @staticmethod
    def add_arguments(parser):
        PygameHandler.add_arguments(parser)
        parser.add_argument("--line-count", type=int, default=20, help="Number of lines")
        parser.add_argument("--line-offset", type=float, default=0.001, help="Time difference between two lines, in seconds")
        parser.add_argument("--dot-count", type=int, default=50, help="Number of dots per line")
        parser.add_argument("--dot-offset", type=float, default=0.0007, help="Time difference between two dots, in seconds")
        parser.add_argument("--amplitude", type=float, default=100, help="Gaussian perturbation amplitude, in pixels")
        parser.add_argument("--sigma", type=float, default=0.1, help="Gaussian perturbation width")
        parser.add_argument("--offset", type=float, default=0, help="Static perturbation offset, in seconds")
        parser.add_argument("--abs-distance", action="store_true", help="Use absolute distance instead of Euclidean norm for spacing lines and dots")
        parser.add_argument("--buffer-size", type=int, default=20, help="Gaussian buffer size")

    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(
            pipe, args, [], PygameHandler.BASE_KWARG_KEYS + ["line_count", "line_offset", "dot_count", "dot_offset", "amplitude", "sigma", "offset", "abs_distance", "buffer_size"])

    def setup(self):
        PygameHandler.setup(self, "BeatViewer: Waves")
        self.t0 = time.time()

    def handle_beat(self):
        self.gaussians.append(gaussian(time.time(), self.gaussian_sigma))
        if len(self.gaussians) > self.gaussians_buffer_size:
            self.gaussians.pop(0)

    def update(self):
        self.window.fill(BACKROUND)
        now = time.time()
        for i in range(self.line_count):
            line_x = (i + .2) * self.width / self.line_count
            dots = []
            dist_i = i - (self.line_count - 1) / 2
            for j in range(self.dot_count):
                dist_j = j - (self.dot_count - 1) / 2
                dot_t = now
                if self.abs_distance:
                    dot_t -= abs(self.line_offset_seconds * dist_i) + abs(self.dot_offset_seconds * dist_j)
                else:
                    dot_t -= (self.line_offset_seconds * dist_i**2 + self.dot_offset_seconds * dist_j**2) ** .5
                dot_x = 0
                for g in self.gaussians:
                    dot_x += g(dot_t)
                dot_x = dot_x * self.gaussian_amplitude + line_x
                dot_y = (j + .5) * self.height / self.dot_count
                dots.append((dot_x, dot_y))
            pygame.draw.aalines(self.window, FOREGROUND, False, dots)
