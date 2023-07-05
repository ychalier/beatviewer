import argparse
import keyboard
import multiprocessing
import os
import time

from ..handlers import HANDLER_LIST
from ..beat_tracker_process import BeatTrackerProcess
from .tool import Tool


try:
    import winsound
    def beep(frequency, duration):
        winsound.Beep(frequency, duration)
except ImportError:
    def beep(frequency, duration):
        os.system(f"beep -f { frequency } -l { duration }")


class Dummy(Tool):

    NAME = "dummy"

    def __init__(self, bpm, handler, onsets=False, keyboard_events=True, print_beat=False, beep_beat=False):
        Tool.__init__(self)
        self.bpm = bpm
        self.handler = handler
        self.onsets = onsets
        self.keyboard_events = keyboard_events
        self.print_beat = print_beat
        self.beep_beat = beep_beat
        self.args = None

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("bpm", type=int)
        parser.add_argument("-o", "--onsets", action="store_true", help="Send onsets every beat and half beat")
        parser.add_argument("-p", "--print", action="store_true", help="Print beat to stdout", dest="print_beat")
        parser.add_argument("-b", "--beep", action="store_true", help="Make noise when a beat occurs", dest="beep_beat")
        parser.add_argument("-k", "--keyboard", action="store_true", help="Enable keyboard shortcuts", dest="keyboard_events")
        handler_subparsers = parser.add_subparsers(dest="dummy_handler", required=True)
        for cls in HANDLER_LIST:
            subparser = handler_subparsers.add_parser(cls.NAME, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            cls.add_arguments(subparser)

    @classmethod
    def from_args(cls, args):
        obj = cls.from_keys(args, ["bpm", "dummy_handler"], ["onsets", "print_beat", "beep_beat", "keyboard_events"])
        obj.args = args
        return obj

    def run(self):
        conn1, conn2 = multiprocessing.Pipe()
        handler = None
        for cls in HANDLER_LIST:
            if cls.NAME == self.handler:
                handler = cls.from_args(conn2, self.args)
                break
        handler.start()
        try:
            conn1.send((BeatTrackerProcess.FLAG_BPM, 0, 0, self.bpm))
            t0 = time.time()
            t1 = t0
            t2 = t0
            while True:
                t = time.time()
                if self.keyboard_events:
                    if keyboard.is_pressed("pageup"):
                        self.bpm += 1
                        conn1.send((BeatTrackerProcess.FLAG_BPM, 0, t - t0, self.bpm))
                        print("BPM:", self.bpm)
                    elif keyboard.is_pressed("pagedown"):
                        self.bpm -= 1
                        conn1.send((BeatTrackerProcess.FLAG_BPM, 0, t - t0, self.bpm))
                        print("BPM:", self.bpm)
                if t - t2 >= 30 / self.bpm:
                    time.sleep(.001)
                if self.onsets and (t - t2 >= 30 / self.bpm or t - t1 >= 60 / self.bpm):
                    t2 = t
                    conn1.send((BeatTrackerProcess.FLAG_ONSET, 0, t - t0, None))
                if t - t1 >= 60 / self.bpm:
                    t1 = t
                    conn1.send((BeatTrackerProcess.FLAG_BEAT, 0, t - t0, None))
                    if self.print_beat:
                        print("·", end="", flush=True)
                    if self.beep_beat:
                        beep(220, 70)
                    continue
                if not handler.is_alive():
                    break
                time.sleep(.001)
        except KeyboardInterrupt:
            pass
        finally:
            handler.kill()
        handler.join()
