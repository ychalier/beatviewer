import itertools
import random
import time

import pygame

from .pygame_handler import PygameHandler


def create_color_pairs(*colors):
    return [(c1, c2) for c1, c2 in itertools.combinations(colors, 2) if c1 != c2]


PALETTES = {
    None: (
        ((0, 0, 0), (255, 255, 255)),
    ),
    "bw": (
        ((0, 0, 0), (255, 255, 255)),
    ),
    "rgb": (
        ((0, 0, 0), (255, 0, 0)),
        ((0, 0, 0), (0, 255, 0)),
        ((0, 0, 0), (0, 0, 255)),
    ),
    "dark": create_color_pairs(
        (53, 4, 57),
        (254, 251, 255),
        (86, 8, 121),
        (53, 4, 57),
        (114, 11, 228)
    ),
    "chromakey": (
        ((0, 255, 0), (53, 4, 57)),
        ((0, 255, 0), (86, 8, 121)),
        ((0, 255, 0), (114, 11, 228)),
        ((0, 255, 0), (91, 12, 68)),
        ((0, 255, 0), (254, 251, 255)),
    ),
    "hippy": create_color_pairs(
        (49, 160, 196),
        (217, 53, 192),
        (117, 210, 120),
        (233, 89, 89),
        (231, 200, 90)
    ),
    "contrast": (
        ((1, 42, 52), (113, 201, 52)),
        ((113, 201, 52), (1, 42, 52)),
    )
}


class Rectangles(PygameHandler):

    NAME = "rectangles"

    def __init__(
            self,
            pipe,
            width=1280,
            height=720,
            fullscreen=False,
            fps=60,
            palette=None,
            scale_curve=.3,
            duration=5,
            beat_breadth=.97,
            onset_breadth=.995,
            onsets=False,
        ):
        PygameHandler.__init__(self, pipe, width, height, fullscreen, fps)
        self.palette = PALETTES[palette]
        self.scale_curve = scale_curve
        self.duration = duration
        self.beat_breadth = beat_breadth
        self.onset_breadth = onset_breadth
        self.handle_onsets = onsets

        self.color_index = random.randint(0, len(self.palette) - 1)
        self.bg_color = self.palette[self.color_index][0]
        self.fg_color = self.palette[self.color_index][1]
        self.time_between_beats = self.duration * 60 / 100
        self.rectangles = []

    @staticmethod
    def add_arguments(parser):
        PygameHandler.add_arguments(parser)
        parser.add_argument("--palette", type=str, default="dark", help="Choose a color palette", choices=[p for p in PALETTES if p is not None])
        parser.add_argument("--scale-curve", type=float, default=0.3, help="Power of non-linear scale progression. Values smaller than 1 produce an ease-out effect.")
        parser.add_argument("--duration", type=float, default=5, help="How long a rectangle takes to go off screen, in seconds")
        parser.add_argument("--beat-breadth", type=float, default=0.97, help="Relative size of inner beat rectangles. Smaller values create thicker rectangles.")
        parser.add_argument("--onset-breadth", type=float, default=0.99, help="Relative size of inner onset rectangles. Smaller values create thicker rectangles.")
        parser.add_argument("--onsets", action="store_true", help="Also handle onsets")

    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(
            pipe, args, [], PygameHandler.BASE_KWARG_KEYS + ["palette", "scale_curve", "duration", "beat_breadth", "onset_breadth", "onsets"])

    def change_color(self):
        previous_color_index = self.color_index
        while self.color_index == previous_color_index and len(self.palette) > 1:
            self.color_index = random.randint(0, len(self.palette) - 1)
        self.bg_color = self.palette[self.color_index][0]
        self.fg_color = self.palette[self.color_index][1]
    
    def handle_beat(self):
        self.rectangles.append((time.time(), self.beat_breadth, 1))
        self.change_color()
    
    def handle_onset(self):
        if not self.handle_onsets:
            return
        self.rectangles.append((time.time(), self.onset_breadth, .5))
        
    def handle_bpm(self, bpm):
        self.time_between_beats = self.duration * 60 / bpm

    def setup(self):
        PygameHandler.setup(self, "BeatViewer: Rectangles")

    def update(self):
        self.window.fill(self.bg_color)
        i = 0
        now = time.time()
        while i < len(self.rectangles):
            t, breadth, opacity = self.rectangles[i]
            scale = ((now - t) / self.time_between_beats) ** self.scale_curve
            if scale < 1.12:
                width = scale * self.width
                height = scale * self.height
                color = (
                    opacity * self.fg_color[0] + (1 - opacity) * self.bg_color[0],
                    opacity * self.fg_color[1] + (1 - opacity) * self.bg_color[1],
                    opacity * self.fg_color[2] + (1 - opacity) * self.bg_color[2],
                )
                pygame.draw.rect(self.window, color, pygame.Rect((self.width - width) // 2, (self.height - height) // 2, width, height))
                width = min(breadth * width, width - 2)
                height = min(breadth * height, height - 2)
                pygame.draw.rect(self.window, self.bg_color, pygame.Rect((self.width - width) // 2, (self.height - height) // 2, width, height))
                i += 1
            else:
                self.rectangles.pop(i)     
