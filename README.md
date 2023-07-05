# BeatViewer

*BeatViewer* is a [Python](https://www.python.org/) program that analyzes an audio stream, extracts [onsets](https://en.wikipedia.org/wiki/Onset_(audio)), [tempo](https://en.wikipedia.org/wiki/Tempo) and [beats](https://en.wikipedia.org/wiki/Beat_(music)), and creates [visuals](https://en.wikipedia.org/wiki/VJing) from them in real time. Feature extraction relies on state-of-the-art [beat tracking algorithms](https://michaelkrzyzaniak.com/Research/Swarms_Preprint.pdf). Visuals are rendered via [Pygame](https://www.pygame.org/news) or external programs such as [OBS Studio](https://obsproject.com/) or any [WebSocket](https://en.wikipedia.org/wiki/WebSocket) client.

For a detailed narration of the birth of the project, watch the [associated video](https://www.youtube.com/watch?v=qv1uJQW-Cpc) (in French, English subtitles are coming).

## Requirements

This program requires a working installation of [Python 3](https://www.python.org/). Tools such as [FFmpeg](https://ffmpeg.org/) and [OBS Studio](https://obsproject.com/) are recommended.

## Installation

1. Download the [latest release](https://github.com/ychalier/beatviewer/releases)
2. Install it with `pip`:
    ```console
    pip install ~/Downloads/beatviewer-1.0.0.tar.gz
    ```

Some resources (OBS script, tools, JS visuals) are available through direct download and are attached to the [latest release](https://github.com/ychalier/beatviewer/releases).

## Configuration

Here is a summary of what you'll need to get started. For more options (file output, tracking parameters, etc.) please refer to the [wiki](https://github.com/ychalier/beatviewer/wiki/).

### Audio Source Selection

By default, BeatViewer uses the default audio input. You can specify an audio device using the `-a <device-id>` parameter. You can get a list of audio devices by using the `-l` flag. You can also execute the module offline, by passing the path to an audio file with the `-f` argument (for now, only WAVE file are supported).

### Visualizer Selection

By default, no visualizer is attached to the tracker, it simply prints dots to stdout when a beat occurs. You can specify a visualizer by typing its name after the beat tracking arguments:

```console
python -m beatviewer <visualizer-name> <visualizer-arguments+>
```

For a quick test, you can try the `galaxy` visualizer. You'll find a list with more options and instructions on the [wiki](https://github.com/ychalier/beatviewer/wiki/).

## Contributing

Contributions are welcomed. For now, performance enhancements and addition of new visualizers are mostly needed. Do not hesitate to submit a pull request with your changes!

## License

This project is licensed under the GPL-3.0 license.

## Troubleshooting

Submit bug reports and feature suggestions in the [issue tracker](https://github.com/ychalier/beatviewer/issues/new/choose).

