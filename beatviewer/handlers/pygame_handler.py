import time

import pygame

from ..beat_handler_process import BeatHandlerProcess


class PygameHandler(BeatHandlerProcess):

    BASE_KWARG_KEYS = ["fps", "width", "height", "fullscreen"]

    def __init__(self, pipe, width=1280, height=720, fullscreen=False, fps=60):
        BeatHandlerProcess.__init__(self, pipe)
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.fps = fps
        self.window = None
        self.last_loop = 0

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("--fps", type=float, default=60, help="Framerate")
        parser.add_argument("--width", type=int, default=1280, help="Window width")
        parser.add_argument("--height", type=int, default=720, help="Window height")
        parser.add_argument("--fullscreen", action="store_true")

    def setup(self, title=None):
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.window = pygame.display.set_mode((self.width, self.height), flags)
        if title is not None:
            pygame.display.set_caption(title)
    
    def close(self):
        pygame.display.quit()

    def update(self):
        raise NotImplementedError

    def loop(self):
        t = time.time()
        if t - self.last_loop <= 1 / self.fps:
            return
        self.last_loop = t
        self.update()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    break
