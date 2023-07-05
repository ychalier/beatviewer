import os
import time

import pygame

from .video_reader import VideoReader
from .video_output import VideoOutput


class VideoPlayer(VideoOutput):

    def __init__(self, path, size=900, noframe=True):
        VideoOutput.__init__(self, path, size)
        self.window = None
        self.noframe = noframe
    
    def setup(self, buffer_kwargs={}):
        VideoOutput.setup(self, buffer_kwargs=buffer_kwargs)
        flags = 0
        if self.noframe:
            flags = pygame.NOFRAME
        self.window = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption(os.path.basename(self.path))
    
    def check_events(self, t):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    break
    
    def blit_current_frame(self, update=True):
        frame = VideoReader.convert_frame(self.video[self.cursor], (self.width, self.height))
        self.window.blit(pygame.surfarray.make_surface(frame), (0, 0))
        if update:
            pygame.display.flip()
    
    def update(self, t):
        self.check_events(t)
        if self.time_of_previous_frame is not None and (t - self.time_of_previous_frame) < 1 / self.video.fps:
            time.sleep(.001)
            return
        self.time_of_previous_frame = t
        self.increment()
        self.blit_current_frame(update=True)

    def run(self):
        self.setup()
        while self.running:
            t = time.time()
            self.update(t)
        self.close()
    
    def close(self):
        VideoOutput.close(self)