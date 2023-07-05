import time

import pygame

from .pygame_handler import PygameHandler


class Tunnel(PygameHandler):

    NAME = "tunnel"

    def __init__(
            self,
            pipe,
            width=1280,
            height=720,
            fullscreen=False,
            fps=60,
            n=20,
            z0=0.05,
        ):
        PygameHandler.__init__(self, pipe, width, height, fullscreen, fps)
        self.n = n
        self.z0 = z0
        self.bg_color = (0, 0, 0)
        self.fg_color = (255, 255, 255)
        self.offset = 0
        self.period = 1
        self.previous_beat_time = 0

    @staticmethod
    def add_arguments(parser):
        PygameHandler.add_arguments(parser)
        parser.add_argument("--n", type=int, default=20, help="Number of tunnel parts")
        parser.add_argument("--z0", type=float, default=0.05, help="Z-index (between 0 and 1) of the camera plane. Lower values increase FOV.")
    
    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(pipe, args, [], PygameHandler.BASE_KWARG_KEYS + ["n", "z0"])

    def setup(self):
        PygameHandler.setup(self, "BeatViewer: Tunnel")

    def handle_beat(self):
        self.previous_beat_time = time.time()

    def handle_bpm(self, bpm):
        self.period = 60 / bpm

    def update(self):
        now = time.time()
        self.offset = (now - self.previous_beat_time) / self.period / self.n
        if self.offset > 1 / self.n:
            self.previous_beat_time = now
            self.offset -= 1 / self.n
        self.window.fill(self.bg_color)
        for i in range(self.n, 0, -1):
            z = i / self.n - self.offset
            if z <= 0:
                continue
            points = []
            for x, y in [(-.5, -.5), (-.5, .5), (.5, .5), (.5, -.5)]:
                points.append([
                    (x * self.z0 / z + .5) * self.width,
                    (y * self.z0 / z + .5) * self.height
                ])
            if i == self.n:
                pygame.draw.aaline(self.window, self.fg_color, (0, 0), points[0])
                pygame.draw.aaline(self.window, self.fg_color, (0, self.height), points[1])
                pygame.draw.aaline(self.window, self.fg_color, (self.width, self.height), points[2])
                pygame.draw.aaline(self.window, self.fg_color, (self.width, 0), points[3])
            pygame.draw.aalines(self.window, self.fg_color, True, points)