import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)

import re
import cairo
import pandas as pd
import numpy as np
import ctypes
import cv2
import os
import shutil
import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font("JetBrainsMonoNerdFont-Regular.ttf", 28)
    dpg.bind_font(default_font)

dpg.set_global_font_scale(0.5)

dpg.configure_app(docking=True, docking_space=True, init_file="mate.ini")
dpg.create_viewport(title='MATE Client', width=1280, height=720)

with dpg.theme() as theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 2)
        dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 2)
        dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 4)
        dpg.add_theme_style(dpg.mvStyleVar_WindowTitleAlign, 0.5, 0.5)
dpg.bind_theme(theme)

class Photosphere():
    def __init__(self, camera):
        camera.add_callback(self.on_new_frame)
        self.recording = []
        self.is_recording = False
        self.is_writing = False
        self.frame_rate = 30
        self.is_reading = False

        with dpg.window(label="Photosphere"):
            dpg.add_slider_int(label="Frame Rate", default_value=self.frame_rate, min_value=1, max_value=30, callback=self.set_frame_rate)
            self.recording_button = dpg.add_button(label="Start Recording", callback=self.on_recording_button)
            dpg.add_separator()
            self.stitch_button = dpg.add_button(label="Stitch", callback=self.on_stitch_button)
    
    def set_frame_rate(self, _, rate):
        self.frame_rate = rate

    def on_recording_button(self, _):
        if self.is_writing:
            return

        self.is_recording = not self.is_recording
        if not self.is_recording:
            dpg.configure_item(self.recording_button, label="Saving recording...")
            self.is_writing = True

            if os.path.exists("photosphere/recording"):
                shutil.rmtree("photosphere/recording")
            os.makedirs("photosphere/recording", exist_ok=True)

            video_writer = cv2.VideoWriter("photosphere/recording/video.avi", cv2.VideoWriter_fourcc(*"MJPG"), 30, (1920, 1080))
            for frame in self.recording:
                video_writer.write(frame)
            video_writer.release()

            self.is_writing = False
            dpg.configure_item(self.recording_button, label="Start Recording")


            # for i, frame in enumerate(self.recording):
            #     cv2.imwrite(f"photosphere/recording/frame_{i + 1}.png", frame)
            
            self.is_writing = False
            self.recording = []

            dpg.configure_item(self.recording_button, label="Start Recording")
        else:
            dpg.configure_item(self.recording_button, label="Recording...")
    
    def on_stitch_button(self, _):
        if self.is_reading:
            return
        
        os.makedirs("photosphere", exist_ok=True)

        if os.path.exists("photosphere/stitch"):
            shutil.rmtree("photosphere/stitch")

        os.makedirs("photosphere/stitch", exist_ok=True)

        self.is_reading = True

        dpg.configure_item(self.stitch_button, label="Setting up")
        video_capture = cv2.VideoCapture("photosphere/recording/video.avi")
        # read all frames
        skip_frames = max(1, 30 // self.frame_rate)
        frame_count = 0
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            if frame_count % skip_frames == 0:
                cv2.imwrite(f"photosphere/stitch/frame_{frame_count // skip_frames + 1}.png", frame)
            
            frame_count += 1
        video_capture.release()

        self.is_reading = False
        
        # os.system("/Applications/PTGui.app/Contents/MacOS/PTGui -createproject photosphere/stitch/*.png -output photosphere/stitch/project.pts")
        # os.system("/Applications/PTGui.app/Contents/MacOS/PTGui photosphere/stitch/project.pts")

        dpg.configure_item(self.stitch_button, label = "Stitch")

    def on_new_frame(self, frame):
        if self.is_recording:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            self.recording.append(frame)
        

class Photogrammetry():
    lib = ctypes.cdll.LoadLibrary("libpgm.dylib")

    lib.run_photogrammetry_session.arg_types = [ctypes.c_char_p]
    lib.run_photogrammetry_session.restype = None

    lib.is_completed.argtypes = []
    lib.is_completed.restype = ctypes.c_bool

    lib.get_progress.argtypes = []
    lib.get_progress.restype = ctypes.c_double

    lib.get_eta.argtypes = []
    lib.get_eta.restype = ctypes.c_double

    lib.stop_photogrammetry_session.argtypes = []
    lib.stop_photogrammetry_session.restype = None

    def set_frame_rate(self, _, frame_rate):
        self.frame_rate = frame_rate

    def on_recording_button(self, _):
        if self.is_writing:
            return
        
        if self.is_recording:
            self.is_recording = False
            os.makedirs("pgm", exist_ok=True)

            if os.path.exists("pgm/recording"):
                shutil.rmtree("pgm/recording")

            os.makedirs("pgm/recording", exist_ok=True)

            dpg.configure_item(self.recording_button, label="Saving Recording")
            self.is_writing = True
            video_writer = cv2.VideoWriter("pgm/recording/video.avi", cv2.VideoWriter_fourcc(*"MJPG"), 30, (800, 600))
            for frame in self.recording:
                video_writer.write(frame)
            video_writer.release()
            self.is_writing = False

            dpg.configure_item(self.recording_button, label="Start Recording")
        else:
            self.is_recording = True
            dpg.configure_item(self.recording_button, label="Recording...")
    
    def update(self):
        progress = self.lib.get_progress()
        eta = self.lib.get_eta()

        dpg.set_value(self.progress_bar, progress)
        dpg.configure_item(self.progress_bar, overlay=f"{100 * progress:.2f}%")
        dpg.set_value(self.eta_indicator, f"ETA: {eta:.2f}s")

    def toggle_reconstruction(self, _):
        if self.is_reading:
            return

        if self.running:
            self.running = False
            self.lib.stop_photogrammetry_session()
            dpg.configure_item(self.reconstruction_button, label="Start Reconstruction")
        else:
            self.running = True

            os.makedirs("pgm", exist_ok=True)
            if os.path.exists("pgm/reconstruction"):
                shutil.rmtree("pgm/reconstruction")
            os.makedirs("pgm/reconstruction/model", exist_ok=True)

            self.is_reading = True

            dpg.configure_item(self.reconstruction_button, label="Setting up")
            video_capture = cv2.VideoCapture("pgm/recording/video.avi")
            # read all frames
            skip_frames = max(1, 30 // self.frame_rate)
            frame_count = 0
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    break

                if frame_count % skip_frames == 0:
                    cv2.imwrite(f"pgm/reconstruction/frame_{frame_count // skip_frames + 1}.png", frame)
                
                frame_count += 1
            video_capture.release()

            self.is_reading = False
                
            # frames = len(os.listdir("pgm/recording"))
            # skip_frames = max(1, 30 // self.frame_rate)
            # for frame in range(1, frames + 1, skip_frames):
            #     shutil.copy(f"pgm/recording/frame_{frame}.png", f"pgm/reconstruction/frame_{frame}.png")

            self.lib.run_photogrammetry_session(b"pgm/reconstruction")
            dpg.configure_item(self.reconstruction_button, label="Stop Reconstruction")

    def __init__(self, camera):
        self.is_recording = False
        self.is_writing = False
        self.is_reading = False
        self.recording = []
        self.running = False
        self.frame_rate = 30

        camera.add_callback(self.on_new_frame)

        with dpg.window(label="Photogrammetry"):
            dpg.add_slider_int(label="Frame Rate", default_value=30, min_value=1, max_value=30, callback=self.set_frame_rate)
            self.recording_button = dpg.add_button(label="Start Recording", callback=self.on_recording_button)
            
            dpg.add_separator()
            dpg.add_spacer()
            
            with dpg.group(horizontal=True):
                self.progress_bar = dpg.add_progress_bar(default_value=0.0)
                self.eta_indicator = dpg.add_text("ETA: 0.0s")

            with dpg.group(horizontal=True):
                self.reconstruction_button = dpg.add_button(label="Start Reconstruction", callback=self.toggle_reconstruction)
                dpg.add_button(label="Open in Preview", callback=lambda: os.system("open pgm/reconstruction/out.usdz"))
                dpg.add_button(label="Open in Meshlab", callback=lambda: os.system("open -a /Applications/MeshLab2023.12.app pgm/reconstruction/model/out.obj"))

    def on_new_frame(self, frame):
        if self.is_recording:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            print("recorded frame")
            self.recording.append(frame)

class CameraStream():
    def __init__(self, port = 5601):
        self.pipeline = Gst.parse_launch(
            # f"udpsrc port={port} ! application/x-rtp,encoding-name=JPEG ! rtpjpegdepay ! jpegdec ! videoconvert ! video/x-raw,format=RGBA ! appsink name=sink"
            f"udpsrc port={port} ! application/x-rtp,encoding-name=H264 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! video/x-raw,format=RGBA ! appsink name=sink"
        )

        self.sink = self.pipeline.get_by_name("sink")
        self.sink.set_property("emit-signals", True)
        self.sink.connect("new-sample", self.on_new_sample, None)
        self.pipeline.set_state(Gst.State.PLAYING)

        self.callbacks = []

        self.stream_dimensions = (640, 480)
        width, height = self.stream_dimensions
        with dpg.texture_registry():
            self.stream_texture_id = dpg.add_raw_texture(
                width=width,
                height=height,
                default_value=np.zeros((height, width, 4), dtype=np.float32),
                format=dpg.mvFormat_Float_rgba
            )
        
    
        self.window = dpg.generate_uuid()    
        with dpg.window(label="Camera Stream", tag=self.window, no_scrollbar=True):
            self.stream_image = dpg.add_image(self.stream_texture_id)

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def update_aspect_ratio(self):
        win_width, win_height = dpg.get_item_rect_size(self.window)
        if win_width == 0 or win_height == 0:
            return

        image_aspect = self.stream_dimensions[0] / self.stream_dimensions[1]
        window_aspect = win_width / win_height

        if window_aspect > image_aspect:
            image_height = win_height
            image_width = int(win_height * image_aspect)
            pos_x = int((win_width - image_width) / 2)
            pos_y = 0
        else:
            image_width = win_width
            image_height = int(win_width / image_aspect)
            pos_x = 0
            pos_y = int((win_height - image_height) / 2)

        dpg.set_item_width(self.stream_image, image_width)
        dpg.set_item_height(self.stream_image, image_height)
        dpg.set_item_pos(self.stream_image, [pos_x, pos_y])
    
    def update(self, frame):
        frame = frame.astype(np.float32) / 255.0

        height, width, _ = frame.shape
        frame_dimensions = (width, height)

        if frame_dimensions != self.stream_dimensions:
            dpg.delete_item(self.stream_texture_id)
            self.stream_dimensions = frame_dimensions
            with dpg.texture_registry():
                self.stream_texture_id = dpg.add_raw_texture(
                    width=width,
                    height=height,
                    default_value=frame,
                    format=dpg.mvFormat_Float_rgba
                )
                dpg.configure_item(self.stream_image, texture_tag=self.stream_texture_id)
        else:
            dpg.set_value(self.stream_texture_id, frame)
        

    def on_new_sample(self, sink, _):
        sample = sink.emit("pull-sample")

        caps = sample.get_caps()
        buffer = sample.get_buffer()

        width = caps.get_structure(0).get_value("width")
        height = caps.get_structure(0).get_value("height")
        
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            print("Failed to map buffer")
            return Gst.FlowReturn.ERROR
        
        frame = np.ndarray(
            (height, width, 4),
            buffer=map_info.data,
            dtype=np.uint8
        )
        self.update(frame)

        for callback in self.callbacks:
            callback(frame)

        buffer.unmap(map_info)

        return Gst.FlowReturn.OK

class Carp():
    def __init__(self):
        self.file_dialog = dpg.generate_uuid()
        self.file = None

        with dpg.file_dialog(directory_selector=False, default_path="~/dev/mate-2025", show=False, callback=self.on_file_select, width=700 ,height=400, id=self.file_dialog):
            dpg.add_file_extension(".csv")

        with dpg.window(label="Carp"):
            with dpg.group(horizontal=True):
                self.file_label = dpg.add_text("Nothing selected")
                dpg.add_button(label="Select File", callback=lambda: dpg.show_item(self.file_dialog))

            dpg.add_separator()

            dpg.add_button(label = "Run", callback=self.on_run_button)

    def on_file_select(self, _, file):
        # dpg.configure_item(self.file_label, label=file['file_name'])
        dpg.set_value(self.file_label, file['file_name'])
        self.file = file['file_path_name']
    
    def on_run_button(self, _):
        vw = cv2.VideoWriter("carp.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 1, (932, 1241))
        for year, *state in pd.read_csv(self.file).values:
            surface = cairo.ImageSurface.create_from_png("illinois.png")
            ctx = cairo.Context(surface)

            regions = [
                "m 216.82162,637.75901 c -1.10607,1.5775 -2.21213,3.15497 -3.41356,4.3095 -1.20143,1.15452 -2.49821,1.88606 -5.68297,11.34232 -3.18476,9.45626 -8.25743,27.63699 -8.37583,35.7971 -0.11839,8.16011 4.7175,6.29918 6.02743,14.44337 1.30992,8.1442 -0.90617,26.29352 -2.6646,38.20699 -1.75844,11.91346 -3.05919,17.59091 -1.83432,21.8778 1.22486,4.28688 4.97531,7.18307 5.15645,9.41243 0.18115,2.22936 -3.20704,3.79187 -4.3036,6.32251 -1.09656,2.53065 0.0985,6.02943 1.77986,14.79163 1.68136,8.76221 3.84902,22.78783 6.85253,26.48943 3.00352,3.7016 6.84287,-2.92078 9.37259,-5.51379 2.52971,-2.59302 3.74973,-1.15657 4.96973,0.27986",
                "m 216.43486,637.06441 c 2.49603,-5.08807 4.99206,-10.17613 7.51212,-13.20018 2.52006,-3.02405 5.06404,-3.98404 7.94411,-7.15214 2.88007,-3.1681 6.09605,-8.54406 11.28019,-12.24013 5.18414,-3.69607 12.33609,-5.71205 17.04018,-8.59213 4.70409,-2.88008 6.96007,-6.62405 8.73611,-8.78408 1.77603,-2.16004 3.07202,-2.73603 5.59209,-5.16011 2.52008,-2.42407 6.26405,-6.69605 9.38412,-12.02418 3.12006,-5.32813 5.61604,-11.71209 9.36014,-16.27218 3.7441,-4.56009 8.73607,-7.29607 12.21614,-10.80016 3.48006,-3.50409 5.44805,-7.77606 10.5602,-11.71215 5.11215,-3.93608 13.36809,-7.53606 21.6242,-11.13611",
                "m 337.33623,519.81964 c 2.32785,-0.60727 4.6557,-1.21453 8.09692,-5.51608 3.44122,-4.30154 7.99562,-12.29705 10.72833,-17.40823 2.73271,-5.11118 3.64359,-7.33777 3.99783,-9.66565 0.35423,-2.32788 0.15181,-4.75689 1.21455,-8.856 1.06274,-4.0991 3.39055,-9.86801 5.5666,-13.96708 2.17606,-4.09907 4.20024,-6.52808 5.31356,-8.55232 1.11332,-2.02424 1.31574,-3.64358 2.27726,-5.06055 0.96152,-1.41696 2.68208,-2.63147 3.69419,-6.32574 1.01211,-3.69426 1.31574,-9.868 4.1497,-15.94072 2.83396,-6.07272 8.19804,-12.04405 11.08255,-15.38402 2.88452,-3.33997 3.28936,-4.04843 2.22662,-7.64149 -1.06274,-3.59305 -3.59296,-10.07042 -4.45325,-14.37191 -0.86029,-4.30149 -0.0506,-6.42688 1.31575,-7.99566 1.36637,-1.56878 3.28934,-2.58087 10.01999,-3.54238 6.73064,-0.96152 18.26846,-1.8724 29.80652,-2.7833",
                "m 432.67698,376.50488 c 5.06055,0.30363 10.1211,0.60727 15.68777,-0.0506 5.56666,-0.65789 11.6392,-2.27723 16.14312,-2.68207 4.50391,-0.40483 7.43897,0.40484 9.71623,1.16393 2.27727,0.75909 3.89661,1.46755 8.34997,2.27725 4.45336,0.8097 11.7404,1.72057 22.36769,-0.3037 10.6273,-2.02427 24.59414,-6.98351 32.438,-9.81742 7.84387,-2.83391 9.56443,-3.54238 11.94292,-4.95935 2.37848,-1.41698 5.41475,-3.54236 8.29929,-6.52813 2.88454,-2.98576 5.61718,-6.8317 7.64142,-10.62715 2.02423,-3.79545 3.33995,-7.54018 4.20024,-11.43685 0.8603,-3.89666 1.26514,-7.94502 1.61938,-10.93076 0.35424,-2.98574 0.65787,-4.90871 3.59304,-8.24872 2.93518,-3.34002 8.50167,-8.09684 14.37197,-13.00562 5.8703,-4.90878 12.04405,-9.96923 17.00342,-13.86588 4.95938,-3.89665 8.70411,-6.62929 13.5623,-9.46323 4.85818,-2.83394 10.82951,-5.769 16.80096,-8.70412",
                "m 612.4277,155.15645 c 0.30363,2.42906 0.60727,4.85812 0.65787,7.33781 0.0506,2.4797 -0.15182,5.00993 -0.8097,8.0969 -0.65788,3.08697 -1.77118,6.73049 -2.68208,9.96927 -0.91091,3.23878 -1.61937,6.07263 -1.77119,9.21021 -0.15181,3.13757 0.25303,6.57868 1.31576,10.77898 1.06273,4.20031 2.78328,9.15955 5.21238,13.96712 2.42909,4.80757 5.56657,9.46318 8.4005,13.1068 2.83394,3.64362 5.36416,6.27506 6.98354,9.9693 1.61938,3.69425 2.32785,8.45107 3.28937,11.68984 0.96151,3.23877 2.17602,4.95933 2.73268,7.2366 0.55666,2.27728 0.45545,5.11113 1.01212,7.23657 0.55667,2.12545 1.77118,3.54237 2.42905,5.81965 0.65788,2.27728 0.75909,5.41476 2.07485,9.8681 1.31577,4.45334 3.846,10.22225 5.76902,13.15737 1.92302,2.93512 3.23874,3.03633 5.06056,5.31362 1.82182,2.27729 4.14963,6.73049 6.4775,9.21016 2.32788,2.47968 4.65568,2.98572 6.5281,4.30149 1.87242,1.31576 3.28934,3.44115 5.00995,4.95932 1.72061,1.51818 3.74479,2.42906 7.0848,3.08694 3.34001,0.65787 7.99562,1.06271 13.71411,0.55664 5.71848,-0.50607 12.49949,-1.923 18.92645,-3.74482 6.42695,-1.82182 12.49949,-4.04842 19.17949,-7.38843 6.68,-3.34 13.96704,-7.7932 19.98914,-12.90441 6.0221,-5.11121 10.77892,-10.88012 14.72619,-16.5986 3.94726,-5.71848 7.08473,-11.38618 9.31139,-16.6492 2.22665,-5.26302 3.54237,-10.12105 4.85811,-14.97918"
            ]
            
            ctx.select_font_face("Comic Sans MS", cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(120.958)
            ctx.move_to(11.884668, 1210.7764)
            ctx.show_text(str(year))

            ctx.set_line_width(10)
            ctx.set_source_rgba(0, 0, 1, 1)

            for region, is_shown in zip(regions, state):
                if is_shown == "Y":
                    move_points = "(?:(m) (-?[\\d.]+),(-?[\\d.]+) ?)"
                    curve_points = "(?:(-?[\\d.]+),(-?[\\d.]+) (-?[\\d.]+),(-?[\\d.]+) (-?[\\d.]+),(-?[\\d.]+) ?)"

                    ctx.move_to(*[float(x) for x in re.search(move_points, region).groups()[1:]])
                    for x in re.findall(curve_points, region):
                        ctx.rel_curve_to(*[float(y) for y in x])

                    ctx.stroke()

            buf = np.ndarray(shape=(1241, 932, 4), dtype=np.uint8, buffer=surface.get_data())
            vw.write(cv2.cvtColor(buf, cv2.COLOR_RGBA2BGR))

        vw.release()

        os.system("open carp.mp4")

class Notes():
    def __init__(self):
        self.window = dpg.generate_uuid()
        with dpg.window(label="Notes", tag = self.window):
            self.input = dpg.add_input_text(default_value=
                "Ship Height (Back Right): 30.5 (colored)\n\n\n\n\n\n\n\n\n\nLength: 189",
                multiline=True
            )
    
    def update(self):
        width = dpg.get_item_width(self.window)
        height = dpg.get_item_height(self.window)

        dpg.set_item_width(self.input, width - 16)
        dpg.set_item_height(self.input, height - 40)



camera_stream1 = CameraStream(5600)
camera_stream2 = CameraStream(5601)
photogrammetry = Photogrammetry(camera = camera_stream2)
photosphere = Photosphere(camera = camera_stream2)
carp = Carp()
notes = Notes()

dpg.setup_dearpygui()
dpg.show_viewport()
try:
    while dpg.is_dearpygui_running():
        camera_stream1.update_aspect_ratio()
        camera_stream2.update_aspect_ratio()
        photogrammetry.update()
        notes.update()

        dpg.render_dearpygui_frame()
except KeyboardInterrupt:
    pass

should_save_config = input("Should I save the config? (y/n)")
if should_save_config.lower() == "y":
    dpg.save_init_file("mate.ini")
    print("Saved config")

dpg.destroy_context()