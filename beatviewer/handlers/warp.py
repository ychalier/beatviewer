import json
import os
import random
import re
import time

from ..beat_handler_process import BeatHandlerProcess
from ..video.video_player import VideoPlayer
from ..video.video_stream import VideoStream


TIMING_FUNCTION_LINEAR = 0
TIMING_FUNCTION_POWER = 1
TIMING_FUNCTION_BEZIER = 2


def cubic_bezier(x1, y1, x2, y2, p, tol=.01):
    t = None
    left = 0
    right = 1
    while True:
        t = .5 * (left + right)    
        x = 3 * x1 * t * ((1 - t) ** 2) + 3 * x2 * (t ** 2) * (1 - t) + t ** 3
        if abs(x - p) < tol:
            break
        if x > p:
            right = t
        else:
            left = t
    return 3 * y1 * t * ((1 - t) ** 2) + 3 * y2 * (t ** 2) * (1 - t) + t ** 3


def buffered_cubic_bezier(x1, y1, x2, y2, tol=.001, step=.001):
    buffer = {0: 0, round(1 / step): 1}
    p = step
    while p < 1:
        buffer[round(p / step)] = cubic_bezier(x1, y1, x2, y2, p, tol=tol)
        p += step
    def aux(q):
        return buffer.get(round(q / step), 0)
    return aux


def parse_timing_argument(string):
    if string is None:
        return TIMING_FUNCTION_LINEAR, []
    match = re.match(r"^([\w\-]+)(?:\((.+)\))?$", string)
    if match.group(1) is None or string == "linear":
        return TIMING_FUNCTION_LINEAR, []
    if match.group(1) == "ease-in":
        return TIMING_FUNCTION_BEZIER, (0.42, 0, 1, 1)
    elif match.group(1) == "ease-out":
        return TIMING_FUNCTION_BEZIER, (0, 0, 0.58, 1)
    elif match.group(1) == "ease-weak":
        return TIMING_FUNCTION_BEZIER, (0.3, 0, 0.7, 1)
    elif match.group(1) == "ease-medium":
        return TIMING_FUNCTION_BEZIER, (0.42, 0, 0.58, 1)
    elif match.group(1) == "ease-strong":
        return TIMING_FUNCTION_BEZIER, (0.75, 0, 0.25, 1)
    elif match.group(1) == "power":
        return TIMING_FUNCTION_POWER, list(map(float, match.group(2).split(",")))
    elif match.group(1) == "bezier":
        return TIMING_FUNCTION_BEZIER, list(map(float, match.group(2).split(",")))
    else:
        raise ValueError("Incorrect timing function: '%s'" % string)


class Warp(BeatHandlerProcess):

    NAME = "warp"

    def __init__(
            self,
            pipe,
            path,
            fps=60,
            rewind=0,
            timing=None,
            before=120,
            after=120,
            margin=120,
            size=900,
            virtual_cam=False,
            prev_threshold=0.1,
            next_threshold=0.1,
            jumpcut=False,
        ):
        BeatHandlerProcess.__init__(self, pipe)
        self.fps = fps
        self.path = path
        self.virtual_cam = virtual_cam
        if self.virtual_cam:
            self.output = VideoStream(path, size, self.fps)
        else:
            self.output = VideoPlayer(path, size)
        self.checkpoints = None
        self.rewind_probability = rewind
        self.period = 1
        self.prev_beat_time = time.time()
        self.next_beat_time = self.prev_beat_time + self.period
        self.prev_video_frame = None
        self.cur_video_frame_index = None
        self.next_video_frame_in = 1
        self.next_checkpoint_index = 1
        self.direction = 1
        timing_argument = parse_timing_argument(timing)
        self.timing_function = timing_argument[0]
        self.timing_args = timing_argument[1]
        self.bezier_curve = None
        self.buffer_before = 0 if jumpcut else before
        self.buffer_after = after
        self.buffer_margin = margin
        self.prev_beat_distance_threshold = prev_threshold
        self.next_beat_distance_threshold = next_threshold
        self.jumpcut = jumpcut
        self.last_loop = 0

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="Path to the video file")
        parser.add_argument("--fps", type=float, default=30, help="Framerate")
        parser.add_argument("--rewind", type=float, default=0, help="Probability of going back in time at each checkpoint")
        parser.add_argument("--timing", type=str, help="Timing function and arguments")
        parser.add_argument("--before", type=int, default=120, help="Number of frames stored in the buffer before its cursor")
        parser.add_argument("--after", type=int, default=120, help="Number of frames stored in the buffer after its cursor")
        parser.add_argument("--margin", type=int, default=120, help="Number of frames above the default buffer size to trigger the cleanup")
        parser.add_argument("--size", type=int, default=900, help="Length of the largest video edge")
        parser.add_argument("--virtual-cam", action="store_true", help="Send video output to a virtual camera instead of a window")
        parser.add_argument("--prev-threshold", type=float, default=0.1, help="Duration (in seconds) above which the timing is updated. Increase to reduce flickering.")
        parser.add_argument("--next-threshold", type=float, default=0.1, help="Duration (in seconds) above which the timing is updated. Increase to reduce flickering.")
        parser.add_argument("--jumpcut", action="store_true", help="Jump to a random checkpoint when a beat occurs instead of warped playback")

    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(
            pipe,
            args,
            ["video_path"], 
            ["fps", "rewind", "timing", "before", "after", "margin", "size",
             "virtual_cam", "prev_threshold","next_threshold", "jumpcut"])

    def setup(self):
        self.output.setup({
            "before": self.buffer_before,
            "after": self.buffer_after,
            "margin": self.buffer_margin
        })
        data_path = os.path.splitext(self.path)[0] + ".json"
        with open(data_path, "r") as file:
            self.checkpoints = json.load(file).get("checkpoints")
        self.prev_video_frame = self.checkpoints[0]
        if self.timing_function == TIMING_FUNCTION_BEZIER:
            self.bezier_curve = buffered_cubic_bezier(*self.timing_args)

    def handle_beat(self):
        t = time.time()
        distance_prev = abs(self.prev_beat_time - t)
        distance_next = abs(self.next_beat_time - t)
        if distance_next < distance_prev and distance_next > self.next_beat_distance_threshold:
            self.prev_beat_time = t - self.period
            self.next_beat_time = t
        elif distance_prev < distance_next and distance_prev > self.prev_beat_distance_threshold:
            self.prev_beat_time = t
            self.next_beat_time = t + self.period

    def handle_bpm(self, bpm):
        self.period = 60 / bpm
        self.next_beat_time = self.prev_beat_time + self.period
    
    def apply_timing_function(self, p):
        if self.timing_function == TIMING_FUNCTION_LINEAR:
            return p
        elif self.timing_function == TIMING_FUNCTION_POWER:
            return p ** self.timing_args[0]
        elif self.timing_function == TIMING_FUNCTION_BEZIER:
            return self.bezier_curve(p)
            
    def get_current_frame_index(self):
        t = time.time()
        p = max(0, min(1, (t - self.prev_beat_time) / (self.next_beat_time - self.prev_beat_time)))        
        if self.jumpcut:
            frame_index = int(self.prev_video_frame + (t - self.prev_beat_time) * self.output.video.fps) % self.output.video.frame_count
        else:
            p = self.apply_timing_function(p)
            frame_index = int(self.prev_video_frame + self.direction * p * self.next_video_frame_in) % self.output.video.frame_count
        return t, p, frame_index
    
    def move_to_next_segment(self, t):
        self.direction = 1
        if random.random() < self.rewind_probability and self.next_checkpoint_index > 0:
            self.direction = -1
        self.prev_video_frame = self.checkpoints[self.next_checkpoint_index]
        if self.jumpcut:
            self.prev_video_frame = random.choice(self.checkpoints)
        elif self.direction == 1:
            self.next_checkpoint_index = (self.next_checkpoint_index + 1) % len(self.checkpoints)
            next_video_frame = self.checkpoints[self.next_checkpoint_index]
            if next_video_frame > self.prev_video_frame:
                self.next_video_frame_in = next_video_frame - self.prev_video_frame
            else:
                self.next_video_frame_in = self.output.video.frame_count - self.prev_video_frame + next_video_frame
        else:
            self.next_checkpoint_index = (self.next_checkpoint_index - 1 + len(self.checkpoints)) % len(self.checkpoints)
            next_video_frame = self.checkpoints[self.next_checkpoint_index]
            if next_video_frame > self.prev_video_frame:
                self.next_video_frame_in = self.prev_video_frame + self.output.video.frame_count - next_video_frame
            else:
                self.next_video_frame_in = self.prev_video_frame - next_video_frame
        self.prev_beat_time = t
        self.next_beat_time = t + self.period

    def loop(self):
        now = time.time()
        if now - self.last_loop <= 1 / self.fps:
            return
        self.last_loop = now
        t, p, frame_index = self.get_current_frame_index()
        if not self.virtual_cam:
            self.output.check_events(t)
            self.running &= self.output.running
        if frame_index != self.output.cursor:
            self.output.cursor = frame_index
            self.output.blit_current_frame(update=True)
        if abs(p - 1) < .001:
            self.move_to_next_segment(t)

    def close(self):
        self.output.close()
        BeatHandlerProcess.close(self)
