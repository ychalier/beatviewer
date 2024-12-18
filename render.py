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
                 vcodec: str = "h264", execute: bool = False):
        self.width = width
        self.height = height
        self.path = path
        self.framerate = framerate
        self.vcodec = vcodec
        self.execute = execute
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
        if self.execute:
            try:
                os.startfile(os.path.realpath(self.path))
            except AttributeError:
                # This may occur depending on platform
                pass


def analyze_audio(audio_path: str) -> tuple[list[BeatTrackingEvent], float]:
    config = Config()
    audio_source = FileAudioSource(config, audio_path, pbar_kwargs={
        "desc": "Analyzing audio"
    })
    tracker = BeatTracker(config, audio_source, register_events=True)
    tracker.run()
    return tracker.events, tracker.frame_index / tracker.sampling_rate_oss


def render(audio_path: str, video_path: str, output_path: str):
    events, duration = analyze_audio(audio_path)
    reader = VideoReader(video_path)
    reader.open()
    aux_path = os.path.join(tempfile.gettempdir(), "beatviewer.mp4")
    output = FFmpegVideoOutput(aux_path, reader.width, reader.height, round(reader.fps))
    with output:
        frame_cursor = 0
        event_cursor = 0
        for i in tqdm.tqdm(range(round(duration * reader.fps)), unit="frame", desc="Encoding video"):
            t = i / reader.fps
            has_beat = False
            while event_cursor < len(events) and events[event_cursor].time < t:
                if events[event_cursor].flag == EventFlag.BEAT:
                    has_beat = True
                event_cursor += 1
            if has_beat:
                frame_cursor = random.randint(0, reader.frame_count - 1)
            frame = reader.convert_frame(reader.read_frame(frame_cursor), transpose=False)
            output.feed(frame)
            frame_cursor = (frame_cursor + 1) % reader.frame_count
    subprocess.Popen([
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-stats",
        "-i", aux_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        output_path,
        "-y"
    ]).wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", type=str)
    parser.add_argument("video_path", type=str)
    parser.add_argument("output_path", type=str)
    args = parser.parse_args()
    render(args.audio_path, args.video_path, args.output_path)


if __name__ == "__main__":
    main()