import json
import os

import pygame

from ..video.video_player import VideoPlayer
from .tool import Tool


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)


class Annotator(Tool, VideoPlayer):

    NAME = "annotator"

    MONITORED_KEYS = [
        pygame.K_RIGHT,
        pygame.K_LEFT,
        pygame.K_SPACE,
        pygame.K_LALT,
        pygame.K_LSHIFT,
        pygame.K_RSHIFT,
        pygame.K_LCTRL
    ]

    def __init__(
            self,
            path, 
            size=900,
            buffer_before=30,
            buffer_after=30,
            buffer_margin=120
        ):
        pygame.init()
        Tool.__init__(self)
        VideoPlayer.__init__(self, path, size=size, noframe=False)
        self.time_of_previous_checkpoint = None
        self.checkpoints = set()
        self.pressed = set()
        self.font16 = pygame.font.SysFont("Consolas", 16)
        self.prev_checkpoint = None
        self.prev_checkpoint_distance = None
        self.next_checkpoint = None
        self.next_checkpoint_distance = None
        self.playback_period = 60 / 100
        self.playback_warping_power = 1.5
        self.buffer_before = buffer_before
        self.buffer_after = buffer_after
        self.buffer_margin = buffer_margin
        self.unused_data = {}
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("path", type=str, help="Path to a video file")
        parser.add_argument("-s", "--size", type=int, default=900, help="Maximum size of the window")
        parser.add_argument("-b", "--buffer-before", type=int, default=30, help="Number of frames stored in the buffer before its cursor")
        parser.add_argument("-a", "--buffer-after", type=int, default=30, help="Number of frames stored in the buffer after its cursor")
        parser.add_argument("-m", "--buffer-margin", type=int, default=120, help="Number of frames above the default buffer size to trigger the cleanup")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["path"], ["size", "buffer_before", "buffer_after", "buffer_margin"])
    
    def setup(self):
        self.load()
        VideoPlayer.setup(self, {
            "before": self.buffer_before,
            "after": self.buffer_after,
            "margin": self.buffer_margin
        })
        self.update_surrounding_checkpoints()
        self.time_of_previous_checkpoint = 0

    def set_cursor(self, i):
        self.cursor = i % self.video.frame_count
        self.update_surrounding_checkpoints()
        self.update_display()
    
    def goto_prev(self):
        self.set_cursor(self.cursor - 1)
    
    def goto_next(self):
        self.set_cursor(self.cursor + 1)

    def goto_prev_checkpoint(self):
        if self.prev_checkpoint is not None:
            self.set_cursor(self.prev_checkpoint)
    
    def goto_next_checkpoint(self):
        if self.next_checkpoint is not None:
            self.set_cursor(self.next_checkpoint)
    
    def goto_start(self):
        self.set_cursor(0)
    
    def goto_end(self):
        self.set_cursor(self.video.frame_count - 1)
    
    def toggle_checkpoint(self):
        if self.cursor in self.checkpoints:
            self.checkpoints.remove(self.cursor)
        else:
            self.checkpoints.add(self.cursor)
        self.update_display()

    def update_surrounding_checkpoints(self):
        self.prev_checkpoint = None
        self.prev_checkpoint_distance = None
        self.next_checkpoint = None
        self.next_checkpoint_distance = None
        if not self.checkpoints:
            return
        for checkpoint in sorted(self.checkpoints):
            if checkpoint < self.cursor:
                self.prev_checkpoint = checkpoint
                self.prev_checkpoint_distance = self.cursor - checkpoint
            elif checkpoint > self.cursor:
                self.next_checkpoint = checkpoint
                self.next_checkpoint_distance = checkpoint - self.cursor
                break
        if self.prev_checkpoint is None and self.checkpoints:
            self.prev_checkpoint = max(self.checkpoints)
            self.prev_checkpoint_distance = self.cursor + self.video.frame_count - self.prev_checkpoint
        if self.next_checkpoint is None and self.checkpoints:
            self.next_checkpoint = min(self.checkpoints)
            self.next_checkpoint_distance = self.video.frame_count - self.cursor + self.next_checkpoint

    def draw_hud(self):
        y = 8
        
        text = self.font16.render(f"#{self.cursor}", True, WHITE, BLACK)
        self.window.blit(text, (8, y))
        y += text.get_height() + 1

        t = self.cursor / self.video.fps
        text = self.font16.render("%02d:%02d:%03d" % (t / 60, t % 60, (t * 1e3) % 1e3), True, WHITE, BLACK)
        self.window.blit(text, (8, y))
        y += text.get_height() + 1
        
        if self.prev_checkpoint is None:
            text = self.font16.render(f"prev: -", True, WHITE, BLACK)
        else:
            text = self.font16.render(f"prev: {self.prev_checkpoint} (-{self.prev_checkpoint_distance})", True, WHITE, BLACK)
        self.window.blit(text, (8, y))
        y += text.get_height() + 1

        if self.next_checkpoint is None:
            text = self.font16.render(f"next: -", True, WHITE, BLACK)
        else:
            text = self.font16.render(f"next: {self.next_checkpoint} (+{self.next_checkpoint_distance})", True, WHITE, BLACK)
        self.window.blit(text, (8, y))
        y += text.get_height() + 1
        
        pygame.draw.rect(self.window, BLACK, pygame.Rect(8, self.height - 24, self.width - 16, 16))
        pygame.draw.line(self.window, WHITE, (16, self.height - 16), (self.width - 16, self.height - 16))
        x = int((self.cursor / (self.video.frame_count - 1)) * (self.width - 32) + 16)
        pygame.draw.line(self.window, WHITE, (x, self.height - 16 + 8), (x, self.height - 16 - 8))
        for checkpoint in self.checkpoints:
            x = int((checkpoint / (self.video.frame_count - 1)) * (self.width - 32) + 16)
            pygame.draw.line(self.window, RED, (x, self.height - 16 + 4), (x, self.height - 16 - 4))

        if self.cursor in self.checkpoints:
            pygame.draw.circle(self.window, RED, (self.width - 75, 75), 60)
    
    def check_events(self, t):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    break
                elif event.key == pygame.K_a and pygame.K_LCTRL in self.pressed:
                    self.goto_start()
                elif event.key == pygame.K_e and pygame.K_LCTRL in self.pressed:
                    self.goto_end()
                elif event.key == pygame.K_s and pygame.K_LCTRL in self.pressed:
                    self.save()
                elif event.key == pygame.K_w and pygame.K_LCTRL in self.pressed:
                    self.running = False
                    break
                elif event.key == pygame.K_RETURN:
                    self.toggle_checkpoint()
                else:
                    for key in self.MONITORED_KEYS:
                        if event.key == key:
                            if key == pygame.K_SPACE:
                                self.time_of_previous_checkpoint = t
                            self.pressed.add(key)
                            break
            elif event.type == pygame.KEYUP:
                for key in self.MONITORED_KEYS:
                    if event.key == key and key in self.pressed:
                        self.pressed.remove(key)
                        break
    
    def update_display(self):
        self.blit_current_frame(update=False)
        self.draw_hud()
        pygame.display.flip()
    
    def update_linear_playback(self, t):
        self.time_of_previous_frame = t
        if pygame.K_LEFT in self.pressed:
            if pygame.K_LCTRL in self.pressed:
                self.goto_prev_checkpoint()
            else:
                self.goto_prev()
            if pygame.K_LSHIFT in self.pressed or pygame.K_RSHIFT in self.pressed:
                self.pressed.remove(pygame.K_LEFT)
        elif pygame.K_RIGHT in self.pressed:
            if pygame.K_LCTRL in self.pressed:
                self.goto_next_checkpoint()
            else:
                self.goto_next()
            if pygame.K_LSHIFT in self.pressed or pygame.K_RSHIFT in self.pressed:
                self.pressed.remove(pygame.K_RIGHT)

    def update_warped_playback(self, t):
        prev_checkpoint = self.prev_checkpoint
        prev_checkpoint_distance = self.prev_checkpoint_distance
        if self.cursor in self.checkpoints:
            prev_checkpoint = self.cursor
            prev_checkpoint_distance = 0
        progress = (t - self.time_of_previous_checkpoint) / self.playback_period
        progress = max(0, min(1, progress)) ** self.playback_warping_power
        if progress >= 1:
            self.time_of_previous_checkpoint = t
        frame_distance = prev_checkpoint_distance + self.next_checkpoint_distance
        self.set_cursor(int(prev_checkpoint + progress * frame_distance))

    def update(self, t):
        self.check_events(t)
        if pygame.K_SPACE in self.pressed and self.checkpoints:
            self.update_warped_playback(t)
            return
        if pygame.K_LALT not in self.pressed and t - self.time_of_previous_frame < 1 / self.video.fps:
            return
        self.update_linear_playback(t)
        self.update_display()
    
    def load(self):
        path = os.path.splitext(self.path)[0] + ".json"
        if os.path.isfile(path):
            with open(path, "r") as file:
                self.unused_data = json.load(file)
            self.checkpoints = set(self.unused_data["checkpoints"])
            del self.unused_data["checkpoints"]

    def save(self):
        path = os.path.splitext(self.path)[0] + ".json"
        with open(path, "w") as file:
            data = { **self.unused_data }
            data.update({
                "path": self.path,
                "frame_count": self.video.frame_count,
                "frame_rate": self.video.fps,
                "width": self.video.width,
                "height": self.video.height,
                "checkpoints": sorted(self.checkpoints),
            })
            json.dump(data, file)

    def run(self):
        VideoPlayer.run(self)