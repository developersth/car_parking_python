import sys, os
from pathlib import Path

# Set YOLO to quiet mode
os.environ['YOLO_VERBOSE'] = 'False'

# Remove the existing `ultralytics` module from sys.modules if already imported
if 'ultralytics' in sys.modules:
    del sys.modules['ultralytics']

# Insert the custom `ultralytics` path at the beginning of sys.path
sys.path.insert(0, r"D:\\ultralytics")

import cv2, time
import os.path
import numpy as np
from datetime import datetime
from collections import defaultdict
from ultralytics import YOLO, solutions
from ultralytics.utils.files import increment_path
import io
import contextlib, logging

# Utility imports
from shapely.geometry import Polygon
from shapely.geometry.point import Point

from cObjectCounter import *
from cAPIClient import *
from common_functions import *

track_history = defaultdict(list)


class VehicleCounter:
    def __init__(
        self,
        camera_name,
        weights="yolov10n.pt",
        source=None,
        device="cpu",
        view_img=False,
        save_img=False,
        exist_ok=False,
        line_thickness=1,
        track_thickness=1,
        region_thickness=1
    ):
        self.weights = weights
        self.source = source
        self.device = device
        self.view_img = view_img
        self.save_img = save_img
        self.exist_ok = exist_ok
        self.line_thickness = line_thickness
        self.track_thickness = track_thickness
        self.region_thickness = region_thickness
        self.camera_name = camera_name
        self.track_history = defaultdict(list)

        # if self.camera_name == "cam_a":
        #     self.model = "yolov10s.pt"

        # Set line points based on the camera name
        self.line_points = self.get_line_points(camera_name)
        
        # Prepare the model
        self.model = YOLO(self.weights)
        self.model.to("cuda") if device == "0" else self.model.to("cpu")

        # if not os.path.exists(self.source):
        #     print("File {} is not exist.".format(str(self.source)))
        #     exit()

        # Video properties
        self.videocapture = cv2.VideoCapture(self.source)
        self.frame_width = int(self.videocapture.get(3))
        self.frame_height = int(self.videocapture.get(4))
        self.fps = int(self.videocapture.get(5))
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # Define classes to track
        self.classes = [2, 5, 6, 7]  # Define your own classes here

        self.apiClient = APIClient('http://127.0.0.1:5000')  # Your Flask server URL

        # Set desired width and height for output video
        self.new_width, self.new_height = self.calculate_new_size(width=1280, height=None)

        # Get the current date and time
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create the new filename with the current date and time
        filename = f"{current_time}.mp4"

        # Initialize video writer
        save_dir = Path(f"D:\\CarPark\\rtsp\\{camera_name}")
        save_dir.mkdir(parents=True, exist_ok=True)
        self.video_writer = cv2.VideoWriter(str(save_dir / filename), self.fourcc, self.fps, (self.new_width, self.new_height))

    def get_line_points(self, camera_name):
        """Define line points based on camera name."""
        line_points_dict = {
            "cam_lab-out": [(100, 300), (1000, 600)],
            "cam_b-out": [(575, 275), (1280, 425)],
            # "cam_mg": [(250, 410), (1100, 400)],
            "cam_b-in": [(50, 400), (500, 250)],
            "cam_a": [(325, 475), (475, 250)],
        }
        return line_points_dict.get(camera_name, [(50, 400), (500, 250)])  # Default if not found

    def calculate_new_size(self, width=None, height=None):
        """Calculate new frame size for resizing."""
        if width is None and height is None:
            return self.frame_width, self.frame_height
        if width is None:
            width = int(self.frame_width * (height / self.frame_height))
        if height is None:
            height = int(self.frame_height * (width / self.frame_width))
        return width, height

    def run(self, stop_event):
        """Run the vehicle counting process on video frames."""
        self.counter = cObjectCounter(
            names=self.model.model.names,
            view_img=False,
            reg_pts=self.line_points,
            draw_tracks=True,
            line_thickness=self.line_thickness,
            view_in_counts=False,
            view_out_counts=False,
        )

        if self.camera_name == "cam_b-in":
            self.counter2 = cObjectCounter(
                names=self.model.model.names,
                view_img=False,
                reg_pts=[(750, 200), (1050, 190)],
                draw_tracks=False,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )
        elif self.camera_name == "cam_a":
            self.counter3 = cObjectCounter(
                names=self.model.model.names,
                view_img=False,
                reg_pts=[(600, 275), (900, 240)], # line b-in
                draw_tracks=False,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )
            self.counter4 = cObjectCounter(
                names=self.model.model.names,
                view_img=False,
                reg_pts=[(910, 220), (875, 320)], # line a-in, a-out
                draw_tracks=False,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )

        if not self.videocapture:
            self.videocapture = cv2.VideoCapture(self.source)

        # Initialize variables for FPS calculation
        prev_frame_time = 0
        new_frame_time = 0

        vid_frame_count = 0
        print('class stop_event: ', stop_event.stop_event)
        while self.videocapture.isOpened() and not stop_event.stop_event:
            print('while stop_event: ', stop_event.stop_event)
            success, im0 = self.videocapture.read()
            if not success:
                print("Video frame is empty or video processing has been successfully completed.")
                time.sleep(0.5)
                continue
            self.videocapture.release()
            self.videocapture = cv2.VideoCapture(self.source)

            # Resize frame
            vid_frame_count += 1
            if vid_frame_count % 1 != 0: # change for process every n frame
                continue 

            im0 = cv2.resize(im0, (self.new_width, self.new_height))

            msg = ""
            msg = self.process(im0)

            # if mqtt_client and ((time.time()-mqtt_time) > mqtt_publish_interval):
            #     mqtt_client.publish(f"SYS/{self.camera_name}", str(msg))
            #     mqtt_time = time.time()

            # Calculate FPS
            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time)
            # print([new_frame_time - prev_frame_time, fps])
            prev_frame_time = new_frame_time

            # Convert FPS to string and display it on the frame
            fps_text = "FPS: " + "{:.3f}".format(fps)
            cv2.putText(im0, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            # Write frame to video
            self.video_writer.write(im0)

            # Display video frame if enabled
            if self.view_img:
                if vid_frame_count == 1:
                    cv2.namedWindow(self.camera_name)
                resized_img = image_resize(im0, width=640)
                cv2.imshow(self.camera_name, resized_img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        self.cleanup()

    def process(self, im0):
        # Track objects
        tracks = self.model.track(im0, persist=True, show=False, classes=self.classes, verbose=False, conf=0.01)
        for result in tracks:
            print(result.verbose())
        # tracks = self.model.track(im0, persist=True, show=False, verbose=True)

        msg = {}
        algorithms = "centroid"
        if self.camera_name == "cam_b-out":
            algorithms = "buttom-right"

        crop_arr = []
        # Count and display counts
        im0, crop_img = self.counter.start_counting(im0, tracks, algorithms)
        if not (crop_img is None):
            crop_arr.append(crop_img)
        if self.camera_name == "cam_b-in":
            _, crop_img = self.counter2.start_counting(im0, tracks)
            if not (crop_img is None):
                crop_arr.append(crop_img)
            counts1 = self.counter.in_counts + self.counter.out_counts
            counts2 = self.counter2.in_counts + self.counter2.out_counts
            # cv2.putText(im0, f'In:{counts1}, Out:{counts2}', (525, 225), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)
            msg = {'line_1': (counts1, self.counter.in_counts, self.counter.out_counts), 'line_2': (counts2, self.counter2.in_counts, self.counter2.out_counts)}
            if self.counter.in_counts_update or self.counter.out_counts_update:
                self.post_event('b', 'in')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)
            if self.counter2.in_counts_update or self.counter2.out_counts_update:
                self.post_event('b', 'out')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)
        elif self.camera_name == "cam_a":
            # counter2.start_counting(im0, tracks, "buttom-right", parent_name="counter2_b-out") # b-out
            _, crop_img = self.counter3.start_counting(im0, tracks, "buttom-right") # b-in
            if not (crop_img is None):
                crop_arr.append(crop_img)
            _, crop_img = self.counter4.start_counting(im0, tracks, "buttom-right") # a
            if not (crop_img is None):
                crop_arr.append(crop_img)

            counts = self.counter.in_counts + self.counter.out_counts
            # counts2 = counter2.in_counts + counter2.out_counts
            counts3 = self.counter3.in_counts + self.counter3.out_counts

            # cv2.putText(im0, f'lab-in:{counts}', (325, 225), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2)
            # cv2.putText(im0, f'b-in:{counts3}', (550, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2)
            # cv2.putText(im0, f'a-in:{counter4.in_counts}, a-out:{counter4.out_counts}', (880, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2)

            msg = {'lab_in': (counts, self.counter.in_counts, self.counter.out_counts)}
            # msg['b-out'] = (counts2, counter2.in_counts, counter2.out_counts)
            msg['b-in'] = (counts3, self.counter3.in_counts, self.counter3.out_counts)

            if self.counter.in_counts_update or self.counter.out_counts_update:
                self.post_event('lab', 'in')
                self.post_save('lab', 'save_image',"http://localhost/images/zone_lab.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_lab.jpg", save_img)

            if self.counter3.in_counts_update or self.counter3.out_counts_update:
                self.post_event('b', 'in')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)

            if self.counter4.in_counts_update:
                self.post_event('a', 'in')
                self.post_save('a', 'save_image',"http://localhost/images/zone_a.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_a.jpg", save_img)

            if self.counter4.out_counts_update:
                self.post_event('a', 'out')
                self.post_save('a', 'save_image',"http://localhost/images/zone_a.jpg")
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite("C:\Apache24\htdocs\images\zone_a.jpg", save_img)

        else:
            counts = self.counter.in_counts + self.counter.out_counts
            # cv2.putText(im0, f'Count:{counts}', (525, 225), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)
            msg = {'line_1': (counts, self.counter.in_counts, self.counter.out_counts)}
            cam = ""
            event = ""
            if "lab-" in self.camera_name:
                cam = 'lab'
            elif "b-" in self.camera_name:
                cam = 'b'
            if "-out" in self.camera_name:
                event = 'out'
            elif "-in" in self.camera_name:
                event = 'in'
            if self.counter.in_counts_update or self.counter.out_counts_update:
                self.post_event(cam, event)
                filePath = "C:\Apache24\htdocs\images\zone_" + cam + ".jpg"
                self.post_save(cam, 'save_image',"http://localhost/images/zone_" + str(cam) + ".jpg")

                # self.post_save(cam, "save_image",filePath)
                save_img = im0
                if len(crop_arr) > 0:
                    save_img = crop_arr[-1]
                cv2.imwrite(filePath, save_img)
                # cv2.imwrite(filePath, im0)
        return msg

    def post_save(self, zone, event, camera):
        response = self.apiClient.post_event(zone, event, camera)
        if not response:
            print("Failed to process event.")

    def post_event(self, zone, event):
        # print("POST SEND")
        response = self.apiClient.post_event(zone, event, self.camera_name)
        if not response:
            print("Failed to process event.")


    def cleanup(self):
        """Release resources."""
        self.video_writer.release()
        self.videocapture.release()
        cv2.destroyAllWindows()

# counter = VehicleCounter(camera_name="b-in", source="D:\\CarPark\\ZONE B-IN\\Camera1_VR-20241025-110855.mp4", view_img=True, save_img=True)
# counter.run()
