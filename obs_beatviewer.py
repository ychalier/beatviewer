import contextlib
import os
import random
import socket

import obspython as obs


ST_SERVER_HOST = "server_host"
ST_SERVER_PORT = "server_port"
ST_BTN_CONNECT = "btn_connect"
ST_BTN_DISCONNECT = "btn_disconnect"
ST_SOCKET_SERVER = "socket_server"
ST_DEBUG_SOURCE = "debug_text_source"
ST_BTN_REFRESH_SOURCES = "btn_refresh_sources"
ST_BTN_BEAT = "btn_beat"
ST_BTN_ONSET = "btn_onset"


@contextlib.contextmanager
def source_ar(source_name):
    try:
        source = obs.obs_get_source_by_name(source_name)
    except:
        print("Source '%s' does not exist" % source_name)
        return
    try:
        yield source
    finally:
        obs.obs_source_release(source)


@contextlib.contextmanager
def data_ar(source_settings=None):
    if not source_settings:
        settings = obs.obs_data_create()
    if source_settings:
        settings = obs.obs_source_get_settings(source_settings)
    try:
        yield settings
    finally:
        obs.obs_data_release(settings)


def populate_list_property_with_source_names(list_property):
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    for source in sources:
        name = obs.obs_source_get_name(source)
        obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sources)


class Visualizer:

    SHORT_NAME = None
    ST_SOURCE = None

    COLOR_FILTER_NAME = "Automatic Color Filter"

    def __init__(self):
        self.source_name = None
        self.source = None
        self.active = False
        self.color_filter = None
        self.previous_opacity = None

    def defaults(self, settings):
        pass

    def create_properties(self, controller, props):
        pass

    def create_or_identify_color_filter(self):
        if self.source is None:
            return
        existing_color_filter = obs.obs_source_get_filter_by_name(self.source, self.COLOR_FILTER_NAME)
        if existing_color_filter is None:
            self.color_filter = obs.obs_source_create_private("color_filter", self.COLOR_FILTER_NAME, None)
            obs.obs_source_filter_add(self.source, self.color_filter)
        else:
            self.color_filter = existing_color_filter

    def release(self):
        if self.color_filter is not None:
            obs.obs_source_release(self.color_filter)
            self.color_filter = None
        if self.source is not None:
            obs.obs_source_release(self.source)
            self.source = None

    def create_source(self, settings):
        self.release()
        self.release()
        self.source = obs.obs_get_source_by_name(self.source_name)
        self.create_or_identify_color_filter()

    def update(self, settings):
        was_active = self.active
        self.active = obs.obs_data_get_bool(settings, self.SHORT_NAME)
        if was_active and not self.active:
            self.stop()
        old_source_name = self.source_name
        self.source_name = obs.obs_data_get_string(settings, self.ST_SOURCE)
        if old_source_name != self.source_name:
            self.create_source(settings)
            
    def set_opacity(self, opacity):
        if opacity == self.previous_opacity:
            return
        self.previous_opacity = opacity
        with data_ar() as settings:
            obs.obs_data_set_int(settings, "opacity", opacity)
            obs.obs_source_update(self.color_filter, settings)

    def handle_beat(self, seconds):
        pass

    def handle_onset(self, seconds):
        pass
    
    def handle_bpm(self, bpm, seconds):
        pass

    def tick(self, seconds):
        pass

    def stop(self):
        pass


class SeekOnBeatVisualizer(Visualizer):

    SHORT_NAME = "sob"
    ST_SOURCE = "sob_source"

    def __init__(self):
        Visualizer.__init__(self)
        self.duration = None

    def defaults(self, settings):
        obs.obs_data_set_default_string(settings, self.ST_SOURCE, "SeekOnBeat")
    
    def create_properties(self, controller, props):
        group = obs.obs_properties_create()
        controller.add_source_list(group, self.ST_SOURCE, "Source name")
        obs.obs_properties_add_group(props, self.SHORT_NAME, "Seek On Beat", obs.OBS_GROUP_CHECKABLE, group)
    
    def update(self, settings):
        Visualizer.update(self, settings)
        self.duration = obs.obs_source_media_get_duration(self.source)
        print("New SeekOnBeat duration:", self.duration)

    def handle_beat(self, seconds):
        Visualizer.handle_beat(self, seconds)
        if not self.active:
            return
        if self.duration is not None and self.duration >= 1:
            obs.obs_source_media_set_time(self.source, random.randint(0, int(self.duration) - 1))
        

class BlinkingSlideshowVisualizer(Visualizer):

    SHORT_NAME = "bs"
    ST_SOURCE = "bs_source"
    ST_FOLDER = "bs_folder"
    ST_DURATION = "bs_duration"
    ST_RANDOM = "bs_random"
    ST_RELATIVE = "bs_relative"
    ST_AUTOSCALE = "bs_autoscale"

    def __init__(self):
        Visualizer.__init__(self)
        self.folder = ""
        self.images = []
        self.index = 0
        self.visible = False
        self.blink_duration = 0.1
        self.random_index = False
        self.bpm = None
        self.relative_to_bpm = False
        self.time_of_previous_beat = 0
        self.auto_scale = True
        self.scale_on_next_tick = 0

    def defaults(self, settings):
        obs.obs_data_set_default_string(settings, self.ST_SOURCE, "BlinkingSlideshow")
        obs.obs_data_set_default_string(settings, self.ST_FOLDER, self.folder)
        obs.obs_data_set_default_bool(settings, self.ST_RANDOM, self.random_index)
        obs.obs_data_set_default_int(settings, self.ST_DURATION, int(self.blink_duration * 1000))
        obs.obs_data_set_default_bool(settings, self.ST_RELATIVE, self.relative_to_bpm)
        obs.obs_data_set_default_bool(settings, self.ST_AUTOSCALE, self.auto_scale)

    def create_properties(self, controller, props):
        group = obs.obs_properties_create()
        controller.add_source_list(group, self.ST_SOURCE, "Source name")
        obs.obs_properties_add_path(group, self.ST_FOLDER, "Images Folder", obs.OBS_PATH_DIRECTORY, None, None)
        obs.obs_properties_add_int(group, self.ST_DURATION, "Blinking Duration (ms)", 1, 1000, 1)
        obs.obs_properties_add_bool(group, self.ST_RELATIVE, "Duration relative to BPM (%)")
        obs.obs_properties_add_bool(group, self.ST_RANDOM, "Random Index Jumps")
        obs.obs_properties_add_bool(group, self.ST_AUTOSCALE, "Automatic Scaling")
        obs.obs_properties_add_group(props, self.SHORT_NAME, "Blinking Slideshow", obs.OBS_GROUP_CHECKABLE, group)

    def scale(self):
        current_scene = obs.obs_scene_from_source(obs.obs_frontend_get_current_scene())
        if current_scene:
            scene_item = obs.obs_scene_find_source(current_scene, self.source_name)
            if scene_item:
                obs.obs_sceneitem_set_bounds_type(scene_item, obs.OBS_BOUNDS_SCALE_INNER)
                video_info = obs.obs_video_info()
                obs.obs_get_video_info(video_info)
                pos = obs.vec2()
                pos.x = 0
                pos.y = 0
                obs.obs_sceneitem_set_pos(scene_item, pos)
                bounds = obs.vec2()
                bounds.x = video_info.base_width
                bounds.y = video_info.base_height
                obs.obs_sceneitem_set_bounds(scene_item, bounds)

    def create_source(self, settings):
        Visualizer.create_source(self, settings)
        if self.auto_scale:
            self.scale()

    def load_images(self):
        if not os.path.isdir(self.folder):
            return
        self.index = 0
        self.images = sorted([
            os.path.join(self.folder, path)
            for path in next(os.walk(self.folder))[2]
        ])
        print("BlinkingSlideshow folder contains %d images" % len(self.images))

    def update(self, settings):
        Visualizer.update(self, settings)        
        self.random_index = obs.obs_data_get_bool(settings, self.ST_RANDOM)
        duration_input_value = obs.obs_data_get_int(settings, self.ST_DURATION)
        if self.relative_to_bpm and self.bpm is not None:
            self.blink_duration = (duration_input_value / 100) * 60 / self.bpm
        else:
            self.blink_duration = duration_input_value / 1000
        self.set_opacity(0)
        old_folder = self.folder
        self.folder = obs.obs_data_get_string(settings, self.ST_FOLDER)
        if old_folder != self.folder:
            print("New BlinkingSlideshow folder:", self.folder)
            self.load_images()

    def handle_beat(self, seconds):
        if not self.active:
            return
        self.time_of_previous_beat = seconds
        self.load_next_image()
        self.set_opacity(100)

    def handle_bpm(self, bpm, seconds):
        self.bpm = bpm

    def load_next_image(self):
        if len(self.images) > 0:
            with data_ar() as settings:
                obs.obs_data_set_string(settings, "file", os.path.realpath(self.images[self.index]))
                obs.obs_source_update(self.source, settings)
                if self.auto_scale:
                    self.scale()
            if self.random_index:
                self.index = random.randint(0, len(self.images) - 1)
            else:
                self.index = (self.index + 1) % len(self.images)

    def tick(self, seconds):
        if not self.active:
            return
        progress = min(1, max(0, (seconds - self.time_of_previous_beat) / self.blink_duration))
        opacity = int((1 - progress ** 4) * 100)
        self.set_opacity(opacity)

    def stop(self):
        self.set_opacity(0)


class Controller:

    def __init__(self):
        self.host = "localhost"
        self.port = 8765
        self.client = None
        self.connected = False
        self.debug_source_name = None
        self.bpm = None
        self.timestamp = 0
        self.source_lists = []
        self.visualizers = [
            SeekOnBeatVisualizer(),
            BlinkingSlideshowVisualizer()
        ]

    def defaults(self, settings):
        obs.obs_data_set_default_string(settings, ST_SERVER_HOST, self.host)
        obs.obs_data_set_default_int(settings, ST_SERVER_PORT, self.port)
        obs.obs_data_set_default_string(settings, ST_DEBUG_SOURCE, "BeatviewerDebug")
        for visualizer in self.visualizers:
            visualizer.defaults(settings)

    def _create_server_properties(self, props):
        def callback_connect(*args):
            self.connect()
        def callback_disconnect(*args):
            self.disconnect()
        group = obs.obs_properties_create()
        obs.obs_properties_add_text(group, ST_SERVER_HOST, "Host", obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_int(group, ST_SERVER_PORT, "Port", 0, 65535, 1)
        obs.obs_properties_add_button(group, ST_BTN_CONNECT, "Connect", callback_connect)
        obs.obs_properties_add_button(group, ST_BTN_DISCONNECT, "Disonnect", callback_disconnect)
        obs.obs_properties_add_group(props, ST_SOCKET_SERVER, "Socket Server", obs.OBS_GROUP_NORMAL, group)

    def create_properties(self, props):
        def callback_refresh(*args):
            self.refresh_source_lists()
        def callback_beat(*args):
            self.handle_beat()
        def callback_onset(*args):
            self.handle_onset()
        obs.obs_properties_add_button(props, ST_BTN_REFRESH_SOURCES, "Refresh Sources", callback_refresh)
        obs.obs_properties_add_button(props, ST_BTN_BEAT, "Beat", callback_beat)
        obs.obs_properties_add_button(props, ST_BTN_ONSET, "Onset", callback_onset)
        self.add_source_list(props, ST_DEBUG_SOURCE, "Debugging Text Source")
        self._create_server_properties(props)
        for visualizer in self.visualizers:
            visualizer.create_properties(self, props)
        self.refresh_source_lists()
        self.update_debug_text()
    
    def update_debug_text(self):
        with source_ar(self.debug_source_name) as source, data_ar() as settings:
            string = "BeatViewer: "
            if self.connected:
                string += "connected "
            else:
                string += "disconnected "
            if self.bpm is not None:
                string += f"// {self.bpm} BPM "
            obs.obs_data_set_string(settings, "text", string.strip())
            obs.obs_source_update(source, settings)

    def connect(self):
        print(f"Connecting socket client to {self.host}:{self.port}")
        if self.client is not None:
            self.disconnect()
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((self.host, self.port))
            self.client.setblocking(False)
            self.connected = True
            print("Connected to server")
        except (ConnectionRefusedError, OSError):
            print("Could not connect to server")
            self.client = None
            self.connected = False
        self.update_debug_text()

    def disconnect(self):
        print("Disconnecting socket client")
        if self.client is not None:
            self.client.close()
            self.client = None
            self.connected = False
        for visualizer in self.visualizers:
            visualizer.stop()
        self.update_debug_text()

    def add_source_list(self, props, name, description):
        source_list = obs.obs_properties_add_list(props, name, description, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        self.source_lists.append(source_list)
        populate_list_property_with_source_names(source_list)

    def refresh_source_lists(self):
        for source_list in self.source_lists:
            populate_list_property_with_source_names(source_list)

    def update(self, settings):
        print("Updating controller")
        host = obs.obs_data_get_string(settings, ST_SERVER_HOST)
        port = obs.obs_data_get_int(settings, ST_SERVER_PORT)
        if host != self.host or port != self.port:
            self.host = host
            self.port = port
            if self.connected:
                self.connect()
        debug_source_name = obs.obs_data_get_string(settings, ST_DEBUG_SOURCE)
        if debug_source_name != self.debug_source_name:
            self.debug_source_name = debug_source_name
            self.update_debug_text()
        for visualizer in self.visualizers:
            visualizer.update(settings)

    def unload(self):
        if not self.connected:
            self.disconnect()
        for visualizer in self.visualizers:
            visualizer.release()

    def handle_beat(self):
        for visualizer in self.visualizers:
            visualizer.handle_beat(self.timestamp)

    def handle_onset(self):
        for visualizer in self.visualizers:
            visualizer.handle_onset(self.timestamp)

    def handle_bpm(self, bpm):
        if bpm != self.bpm:
            self.bpm = bpm
            self.update_debug_text()
        for visualizer in self.visualizers:
            visualizer.handle_bpm(bpm, self.timestamp)

    def handle_packet(self, packet):
        if packet == b"\x00\x00":
            self.handle_beat()
        elif packet == b"\x00\x01":
            self.handle_onset()
        else:
            bpm = int.from_bytes(packet, byteorder="big", signed=False)
            self.handle_bpm(bpm)

    def tick(self, seconds):
        self.timestamp += seconds
        if self.client is not None and self.connected:
            try:
                packet = self.client.recv(2)
                self.handle_packet(packet)
            except BlockingIOError:
                pass
            except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
                print("Socket server just closed")
                self.disconnect()
                return
        for visualizer in self.visualizers:
            visualizer.tick(self.timestamp)


c = Controller()


###############################################################################
# STARTUP                                                                     #
###############################################################################


def script_defaults(settings):
    global c
    c.defaults(settings)


def script_description():
    return (
        "<b>BeatViewer.</b> Track beats in a music stream. To get started, start the external program with the <code>socket</code> handler."
    )


def script_update(settings):
    global c
    c.update(settings)


def script_properties():
    global c
    props = obs.obs_properties_create()
    c.create_properties(props)
    return props


###############################################################################
# RUNTIME                                                                     #
###############################################################################


def script_tick(seconds):
    global c
    c.tick(seconds)


###############################################################################
# CLOSURE                                                                     #
###############################################################################


def script_unload():
    global c
    c.unload()
