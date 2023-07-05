import argparse
import multiprocessing
import logging
import os
import time

import sounddevice

from .handlers import HANDLER_LIST
from .tools import TOOL_LIST
from .beat_tracker import BeatTracker
from .beat_tracker_process import BeatTrackerProcess
from .config import Config
from .audio_source.live_audio_source import LiveAudioSource
from .audio_source.file_audio_source import FileAudioSource


def print_table(table, padx=4):
    for i in range(len(table)):
        table[i] = list(map(str, table[i]))
    widths = [0] * len(table[0])
    for row in table:
        for j, col in enumerate(row):
            widths[j] = max(widths[j], len(col))
    for row in table:
        for j, col in enumerate(row):
            print(col, end=" " * (widths[j] - len(col) + padx))
        print("")


def get_action_tool(args):
    for cls in TOOL_LIST:
        if cls.NAME == args.action:
            return cls.from_args(args)
    return None


def get_action_handler(args, conn):
    for cls in HANDLER_LIST:
        if cls.NAME == args.action:
            return cls.from_args(conn, args)
    return None


def print_audio_device_list():
    hostapis_info = sounddevice.query_hostapis()
    devices_info = sounddevice.query_devices()
    table = []
    default_device = hostapis_info[0]["default_input_device"]
    for device in devices_info:
        if device["max_input_channels"] == 0:
            continue
        host = hostapis_info[device["hostapi"]]
        table.append([
            str(device["index"]) + ("<" if device["index"] == default_device else ""),
            f"{device['max_input_channels']} in, {device['max_output_channels']} out",
            f"{device['default_low_input_latency']:.2f} ms - {device['default_high_input_latency']:.2f} ms",
            f"{(device['default_samplerate'] / 1000):.1f} kHz",
            host["name"],
            device["name"],
        ])
    print_table(table)

LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(message)s"

def main():
    logging.basicConfig(level=logging.INFO, filename="beatviewer.log", format=LOG_FORMAT)
    logging.info("Hello, World!")
    logging.info("Main process has PID %d", os.getpid())
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-a", "--audio-device", type=int, default=sounddevice.default.device[0], help="Audio device index")
    parser.add_argument("-l", "--list-audio-devices", action="store_true", help="Show the list of available audio devices and exit")
    parser.add_argument("-f", "--audio-file", type=str, default=None, help="Path to a local audio file for 'offline' beat tracking")
    parser.add_argument("-t", "--realtime", action="store_true", help="Make offline beat tracking realtime")
    parser.add_argument("-g", "--graph", action="store_true", help="Plot extracted audio features for in-depth analysis")
    parser.add_argument("-gf", "--graph-fps", type=float, default=30, help="Refresh rate for the audio features graph")
    parser.add_argument("-c", "--config", type=str, default=None, help="Path to a configuration file (see default 'config.txt')")
    parser.add_argument("-k", "--keyboard-events", action="store_true", help="Monitor keyboard events")
    parser.add_argument("-r", "--record-path", type=str, default=None, help="Record the the audio stream to a local file")
    parser.add_argument("-o", "--output-path", type=str, default=None, help="Export the beats, onsets and BPM data to a CSV file")#
    action_subparsers = parser.add_subparsers(dest="action")
    for cls in HANDLER_LIST + TOOL_LIST:
        subparser = action_subparsers.add_parser(cls.NAME, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        cls.add_arguments(subparser)

    args = parser.parse_args()
    if args.list_audio_devices:
        print_audio_device_list()
        parser.exit(0)

    tool = get_action_tool(args)
    if tool is not None:
        tool.run()
        parser.exit(0)

    if args.config is not None:
        logging.info("Loading config from %s", args.config)
        config = Config.from_file(args.config)
    else:
        logging.info("Using default config")
        config = Config()

    if args.audio_file is None:
        audio_source = LiveAudioSource(config, args.audio_device, args.record_path)
    else:
        audio_source = FileAudioSource(config, args.audio_file, realtime=args.realtime, record_path=args.record_path)

    tracker_kwargs = {
        "show_graph": args.graph,
        "graph_fps": args.graph_fps,
        "keyboard_events": args.keyboard_events,
        "output_path": args.output_path,
    }

    if args.action is None:
        def beat_callback():
            print(".", end="", flush=True)
        BeatTracker(config, audio_source, beat_callback=beat_callback, **tracker_kwargs).run()
    else:
        conn1, conn2 = multiprocessing.Pipe()
        tracker = BeatTrackerProcess(config, audio_source, conn1, **tracker_kwargs)
        handler = get_action_handler(args, conn2)
        logging.info("Starting tracker")
        tracker.start()
        logging.info("Starting handler")
        handler.start()
        logging.info("Entering main loop")
        try:
            while True:
                time.sleep(1)
                if not tracker.is_alive():
                    logging.info("Tracker process is not alive, breaking main loop")
                    break
                if not handler.is_alive():
                    logging.info("Handler process is not alive, breaking main loop")
                    break
        except KeyboardInterrupt:
            pass
        finally:
            logging.info("Killing tracker and handler")
            tracker.kill()
            handler.kill()
        logging.info("Joining tracker and handler")
        tracker.join()
        handler.join()

    logging.info("Goodbye!")