import threading
import time

from .video_reader import VideoReader


def circular_interval(size, begin, end):
    begin %= size
    end %= size
    if begin > end:
        return set(range(begin, size)).union(range(end + 1))
    return set(range(begin, end + 1))


class VideoBuffer(VideoReader, threading.Thread):

    def __init__(self, path, before=120, after=120, margin=120):
        VideoReader.__init__(self, path)
        threading.Thread.__init__(self, daemon=True)
        self.before = before
        self.after = after
        self.size = self.before + self.after + 1
        self.buffer = {}
        self.center = None
        self.running = True
        self.changed = False
        self.lock_ready = threading.Lock()
        self.lock_ready.acquire()
        self.buffered_frames = 0
        self.margin = margin

    def setup(self):
        self.open()
        if self.size > self.frame_count:
            if self.frame_count % 2 == 0:
                self.before = self.frame_count // 2 - 1
                self.after = self.frame_count // 2
            else:
                self.before = self.frame_count // 2
                self.after = self.frame_count // 2
        self.center = 0
        self.changed = True
        self.update_buffer()
        self.lock_ready.release()
    
    def wait_until_ready(self):
        self.lock_ready.acquire()

    def interval(self):
        return circular_interval(self.frame_count, self.center - self.before, self.center + self.after)

    def in_interval(self, i):
        begin = (self.center - self.before) % self.frame_count
        end = (self.center + self.after) % self.frame_count
        if begin > end:
            return i >= begin or i <= end + 1
        return i >= begin and i <= end + 1

    def update_buffer(self):
        self.changed = False
        interval = self.interval()
        if self.buffered_frames > self.size + self.margin:
            indices_to_delete = set(self.buffer.keys()).difference(interval)
            for i in indices_to_delete:
                del self.buffer[i]
                self.buffered_frames -= 1
        indices_to_add = interval.difference(self.buffer.keys())
        for i in sorted(indices_to_add):
            # If a frame outside buffer range is accessed while the buffer is
            # filling, we can abort the current operation: next frames will be
            # useless.
            if self.changed and not self.in_interval(self.center):
                return
            self.buffer[i] = self.read_frame(i)
            self.buffered_frames += 1
    
    def __getitem__(self, i):
        self.changed = i != self.center
        self.center = i
        while not i in self.buffer and self.running:
            time.sleep(.001) # TODO: consider using a lock?
        return self.buffer[i]
    
    def terminate(self):
        self.running = False

    def run(self):
        self.setup()
        while self.running:
            if self.changed:
                self.update_buffer()
            else:
                time.sleep(.001)
        self.close()