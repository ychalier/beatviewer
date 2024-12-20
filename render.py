import argparse
import os
import random
import subprocess
import tempfile

import numpy
import tqdm

from beatviewer import BeatTracker, Config, FileAudioSource
from beatviewer.video.video_reader import VideoReader
from beatviewer.beat_tracker import EventFlag, BeatTrackingEvent


class FFmpegVideoOutput:

    def __init__(self, path: str, width: int, height: int, framerate: int,
                 vcodec: str = "h264"):
        self.width = width
        self.height = height
        self.path = path
        self.framerate = framerate
        self.vcodec = vcodec
        self.process = None

    def __enter__(self):
        dirname = os.path.dirname(self.path)
        if not os.path.isdir(dirname) and dirname != "":
            os.makedirs(dirname)
        self.process = subprocess.Popen([
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec","rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", f"{self.framerate}",
            "-i", "-",
            "-r", f"{self.framerate}",
            "-pix_fmt", "yuv420p",
            "-an",
            "-vcodec", self.vcodec,
            self.path,
            "-y"
        ], stdin=subprocess.PIPE)
        return self

    def feed(self, frame: numpy.ndarray):
        self.process.stdin.write(frame.astype(numpy.uint8).tobytes())

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.process.stdin.close()
        self.process.wait()


class Renderer:

    def __init__(self, audio_path: str, video_path: str, output_path: str):
        self.audio_path = audio_path
        self.video_path = video_path
        self.output_path = output_path
        self.events: list[BeatTrackingEvent] = []
        self.duration: float = 0
        self.frame_cursor: float = -1
        self.event_cursor: int = 0
        self.reader = VideoReader(self.video_path)

    def analyze_audio(self):
        config = Config()
        audio_source = FileAudioSource(config, self.audio_path, pbar_kwargs={
            "desc": "Analyzing audio"
        })
        tracker = BeatTracker(config, audio_source, register_events=True, warmup=True)
        tracker.run()
        self.events = tracker.events
        self.duration = tracker.frame_index / tracker.sampling_rate_oss

    def move_event_cursor(self, t: float) -> bool:
        has_beat = False
        while self.event_cursor < len(self.events) and self.events[self.event_cursor].time < t:
            if self.events[self.event_cursor].flag == EventFlag.BEAT:
                has_beat = True
            self.event_cursor += 1
        return has_beat
    
    def update_frame_cursor(self, frame_index: int, has_beat: bool):
        raise NotImplementedError()
    
    def render_output(self, aux_path: str):
        subprocess.Popen([
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-stats",
            "-i", aux_path,
            "-i", self.audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            self.output_path,
            "-y"
        ]).wait()

    def run(self):
        self.analyze_audio()
        self.reader.open()
        aux_path = os.path.join(tempfile.gettempdir(), "foo.mp4")
        output = FFmpegVideoOutput(aux_path, self.reader.width, self.reader.height, round(self.reader.fps))
        with output:
            for i in tqdm.tqdm(range(round(self.duration * self.reader.fps)), unit="frame", desc="Encoding video"):
                t = i / self.reader.fps
                has_beat = self.move_event_cursor(t)
                self.update_frame_cursor(i, has_beat)
                frame = self.reader.read_frame(int(self.frame_cursor))
                output.feed(self.reader.convert_frame(frame, transpose=False))
        self.render_output(aux_path)


class SeekOnBeatRenderer(Renderer):

    def update_frame_cursor(self, frame_index: int, has_beat: bool):
        if has_beat:
            self.frame_cursor = random.randint(-1, self.reader.frame_count - 2)
        self.frame_cursor = (self.frame_cursor + 1) % self.reader.frame_count


class SlowDownRenderer(Renderer):

    def __init__(self, audio_path: str, video_path: str, output_path: str, decay: float, jumpcut: bool):
        Renderer.__init__(self, audio_path, video_path, output_path)
        self.decay = decay
        self.jumpcut = jumpcut
        self.playback_speed = 1
    
    def update_frame_cursor(self, frame_index: int, has_beat: bool):
        if has_beat:
            self.playback_speed = 1
            if self.jumpcut:
                self.frame_cursor = frame_index % self.reader.frame_count - 1
        self.frame_cursor += self.playback_speed
        if self.frame_cursor >= self.reader.frame_count:
            self.frame_cursor -= self.reader.frame_count
        self.playback_speed *= self.decay


def pipeline(audio_path: str, video_path: str, output_path: str, mode: str,
             decay: float = 0.9, jumpcut: bool = False, execute: bool = True):
    base_args = [audio_path, video_path, output_path]
    if mode == "seek":
        renderer = SeekOnBeatRenderer(*base_args)
    elif mode == "slow":
        renderer = SlowDownRenderer(*base_args, decay=decay, jumpcut=jumpcut)
    else:
        raise ValueError(f"Invalid mode: {mode}")
    renderer.run()
    if execute:
        try:
            os.startfile(os.path.realpath(output_path))
        except AttributeError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", type=str)
    parser.add_argument("video_path", type=str)
    parser.add_argument("output_path", type=str)
    parser.add_argument("-m", "--mode", type=str, default="seek", choices=["seek", "slow"])
    parser.add_argument("-d", "--decay", type=float, default=0.9)
    parser.add_argument("-j", "--jumpcut", action="store_true")
    args = parser.parse_args()
    pipeline(args.audio_path, args.video_path, args.output_path, args.mode,
             args.decay, args.jumpcut)


if __name__ == "__main__":
    main()