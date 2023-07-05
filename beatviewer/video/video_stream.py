import pyvirtualcam

from .video_reader import VideoReader
from .video_output import VideoOutput


class VideoStream(VideoOutput):

    def __init__(self, path, size=900, fps=60):
        VideoOutput.__init__(self, path, size)
        self.camera = None
        self.fps = fps
    
    def setup(self, buffer_kwargs={}):
        VideoOutput.setup(self, buffer_kwargs=buffer_kwargs)
        self.camera = pyvirtualcam.Camera(self.width, self.height, self.fps) # TODO: Which FPS value to set?
    
    def blit_current_frame(self, update=True):
        frame = VideoReader.convert_frame(self.video[self.cursor], (self.width, self.height), transpose=False)
        self.camera.send(frame)
    
    def close(self):
        VideoOutput.close(self)
        self.camera.close()