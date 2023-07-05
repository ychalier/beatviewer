from .video_buffer import VideoBuffer


class VideoOutput:

    def __init__(self, path, size=900):
        self.path = path
        self.size = size
        self.running = True
        self.video = None
        self.cursor = 0
        self.width = None
        self.height = None
        self.time_of_previous_frame = 0
    
    def setup(self, buffer_kwargs={}):
        self.video = VideoBuffer(self.path, **buffer_kwargs)
        self.video.start()
        self.video.wait_until_ready()
        aspect = self.video.width / self.video.height
        if aspect >= 1:
            self.width = self.size
            self.height = int(self.size / aspect)
        else:
            self.width = int(self.size * aspect)
            self.height = self.size
    
    def increment(self):
        self.cursor = (self.cursor + 1) % self.video.frame_count
    
    def blit_current_frame(self, update=True):
        raise NotImplementedError
    
    def close(self):
        self.video.terminate()
        self.video.join()