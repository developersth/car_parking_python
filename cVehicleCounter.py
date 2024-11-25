import sys, os
from pathlib import Path
import cv2
import time
import numpy as np
from datetime import datetime
from collections import defaultdict
from ultralytics import YOLO
import threading
from queue import Queue
import torch

# Set YOLO to quiet mode
os.environ['YOLO_VERBOSE'] = 'False'

# Remove the existing `ultralytics` module from sys.modules if already imported
if 'ultralytics' in sys.modules:
    del sys.modules['ultralytics']

# Insert the custom `ultralytics` path at the beginning of sys.path
sys.path.insert(0, r"D:\\ultralytics")

from cObjectCounter import *
from cAPIClient import *
from common_functions import *

track_history = defaultdict(list)

class VehicleCounter:
    def __init__(
        self,
        camera_name,
        weights="yolov10s.pt",
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
        self.img = None
        self.stop_event = threading.Event()
        self.image_queue = Queue(maxsize=10)

        if 'lab-out' in self.camera_name:
            self.weights = "yolov10n.pt"
        # elif 'b-in' in self.camera_name:
        #     self.weights = "yolov10s.pt"

        # Set line points based on the camera name
        self.line_points = self.get_line_points(camera_name)
        
        # Prepare the model
        # Check for CUDA device and set it
        mydevice = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = mydevice
        print(f'Using device: {self.device}')
        self.model = YOLO(self.weights, self.device)
        # self.model.to("cuda") if device == "0" else self.model.to("cpu")

        # Video properties
        self.videocapture = cv2.VideoCapture(self.source)
        self.frame_width = int(self.videocapture.get(3))
        self.frame_height = int(self.videocapture.get(4))
        self.fps = 30 #int(self.videocapture.get(5))
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # Define classes to track
        self.classes = [2, 5, 6, 7]  # Define your own classes here

        self.apiClient = APIClient('http://127.0.0.1:5000')  # Your Flask server URL

        # Set desired width and height for output video
        self.new_width, self.new_height = self.calculate_new_size(width=1280, height=None)
        self.vdo_width, self.vdo_height = self.calculate_new_size(width=640, height=None)

        # Get the current date and time
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create the new filename with the current date and time
        filename = f"{current_time}.mp4"

        # Initialize video writer
        save_dir = Path(f"D:\\CarPark\\rtsp\\{camera_name}")
        save_dir.mkdir(parents=True, exist_ok=True)
        self.video_writer = cv2.VideoWriter(str(save_dir / filename), self.fourcc, self.fps, (self.vdo_width, self.vdo_height))

        self.bLoop=True

    def get_line_points(self, camera_name):
        """Define line points based on camera name."""
        line_points_dict = {
            "cam_lab-out": [(100, 300), (1000, 600)],
            "cam_b-out": [(575, 275), (1280, 425)],
            "cam_b-in": [(50, 400), (500, 250)],
            "cam_main": [(325, 475), (475, 250)],
            "cam_mg": [(400, 140), (750, 140)]
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

    def collect_images(self):
        # Initialize variables for FPS calculation
        prev_frame_time = 0
        new_frame_time = 0
 
        """Thread function to collect images from the camera stream."""
        while self.bLoop:
            success, im0 = self.videocapture.read()
            if not success:
                print("Video frame is empty or video processing has been successfully completed.")
                break
            im0 = cv2.resize(im0, (self.new_width, self.new_height))

            # Calculate FPS
            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time

            # Convert FPS to string and display it on the frame
            fps_text = "RAW FPS: " + "{:02.1f}".format(fps)
            cv2.putText(im0, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(im0, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            if not self.image_queue.full():
                self.image_queue.put(im0)
            else:
                self.image_queue.get()  # Remove the oldest frame if queue is full
                self.image_queue.put(im0)
            # time.sleep(0.075)
        self.videocapture.release()

    def process_images(self):
        """Thread function to process images and display results."""
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
                reg_pts=[(750, 200), (1080,189)],
                draw_tracks=True,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )
        elif self.camera_name == "cam_main":
            self.counter3 = cObjectCounter(
                names=self.model.model.names,
                view_img=False,
                reg_pts=[(600, 250), (950, 245)], # line b-in
                draw_tracks=True,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )
            # self.counter4 = cObjectCounter(
            #     names=self.model.model.names,
            #     view_img=False,
            #     reg_pts=[(910, 220), (875, 320)], # line a-in, a-out
            #     draw_tracks=True,
            #     line_thickness=self.line_thickness,
            #     view_in_counts=False,
            #     view_out_counts=False,
            # )

        # Initialize variables for FPS calculation
        prev_frame_time = 0
        new_frame_time = 0
        frame_count = 0

        while self.bLoop:
            if not self.image_queue.empty():
                im0 = self.image_queue.get()
                msg, update = self.process(im0)
                frame_count += 1

                # Calculate FPS
                new_frame_time = time.time()
                fps = 1 / (new_frame_time - prev_frame_time)
                prev_frame_time = new_frame_time

                # Convert FPS to string and display it on the frame
                # fps_text = "FPS: " + "{:.3f}".format(fps)
                fps_text = "OUT FPS: " + "{:02.1f}".format(fps)
                cv2.putText(im0, fps_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4, cv2.LINE_AA)  # Black outline
                cv2.putText(im0, fps_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                frame_text = "FRAME_COUNT: " + "{}".format(frame_count)
                # cv2.putText(im0, fps_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(im0, frame_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4, cv2.LINE_AA)  # Black outline
                cv2.putText(im0, frame_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)  # White text

                y_axis = 135
                for u in update:
                    txt = u
                    cv2.putText(im0, txt, (10, y_axis), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4, cv2.LINE_AA)  # Black outline
                    cv2.putText(im0, txt, (10, y_axis), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)  # White text
                    y_axis += 35

                # Write frame to video
                resized_img = image_resize(im0, width=640)
                self.video_writer.write(resized_img)

                # Display video frame if enabled
                if self.view_img:
                    cv2.imshow(self.camera_name, resized_img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.bLoop=False
                        break

        self.cleanup()

    def process(self, im0):
        # Track objects
        tracks = self.model.track(im0, persist=True, show=False, classes=self.classes, verbose=False, conf=0.01)
        msg = {}
        update = []
        algorithms = "centroid"
        if self.camera_name == "cam_b-out":
            algorithms = "buttom-right"

        crop_arr = {}
        # Count and display counts
        im0, crop_img = self.counter.start_counting(im0, tracks, algorithms)

        cam = ""
        if "lab-" in self.camera_name or "main" in self.camera_name:
            cam = 'lab'
        elif "b-" in self.camera_name:
            cam = 'b'
        elif "mg" in self.camera_name:
            cam = 'a'
        if not (crop_img is None):
            crop_arr[cam] = crop_img

        if self.camera_name == "cam_b-in":
            _, crop_img = self.counter2.start_counting(im0, tracks)
            if not (crop_img is None):
                crop_arr['b'] = crop_img
            counts1 = self.counter.in_counts + self.counter.out_counts
            counts2 = self.counter2.in_counts + self.counter2.out_counts
            msg = {'line_1': (counts1, self.counter.in_counts, self.counter.out_counts), 'line_2': (counts2, self.counter2.in_counts, self.counter2.out_counts)}
            if self.counter.in_counts_update or self.counter.out_counts_update:
                self.post_event('b', 'in')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                self.save_crop(im0, crop_arr, 'b')
                # save_img = im0
                # if len(crop_arr) > 0:
                #     save_img = crop_arr[-1]
                # if 'b' in crop_arr:
                #     save_img = crop_arr['b']
                # cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)
            if self.counter2.in_counts_update or self.counter2.out_counts_update:
                self.post_event('b', 'out')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                self.save_crop(im0, crop_arr, 'b')
                # save_img = im0
                # if 'b' in crop_arr:
                #     save_img = crop_arr['b']
                # cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)

            txt = "b1: i={}, o={}".format(self.counter.in_counts, self.counter.out_counts)
            update.append(txt)
            txt = "b2: i={}, o={}".format(self.counter2.in_counts, self.counter2.out_counts)
            update.append(txt)

        elif self.camera_name == "cam_main":
            _, crop_img = self.counter3.start_counting(im0, tracks, "buttom-right") # b-in
            if not (crop_img is None):
                crop_arr['b'] = crop_img
                # crop_arr.append(crop_img)
            # _, crop_img = self.counter4.start_counting(im0, tracks, "buttom-right") # a
            # if not (crop_img is None):
            #     crop_arr.append(crop_img)

            counts = self.counter.in_counts + self.counter.out_counts
            counts3 = self.counter3.in_counts + self.counter3.out_counts
            msg = {'lab_in': (counts, self.counter.in_counts, self.counter.out_counts)}
            msg['b-in'] = (counts3, self.counter3.in_counts, self.counter3.out_counts)

            txt = "lab : i={}, o={}".format(self.counter.in_counts, self.counter.out_counts)
            update.append(txt)
            txt = "b-in: i={}, o={}".format(self.counter3.in_counts, self.counter3.out_counts)
            update.append(txt)
            # txt = "   a: i={}, o={}".format(self.counter4.in_counts, self.counter4.out_counts)
            # update.append(txt)

            if self.counter.in_counts_update:
                self.post_event('lab', 'in')
                self.post_save('lab', 'save_image',"http://localhost/images/zone_lab.jpg")
                self.save_crop(im0, crop_arr, 'lab')
                # save_img = im0
                # if len(crop_arr) > 0:
                #     save_img = crop_arr[-1]
                # cv2.imwrite("C:\Apache24\htdocs\images\zone_lab.jpg", save_img)
            if self.counter.out_counts_update:
                self.post_event('lab', 'out')
                self.post_save('lab', 'save_image',"http://localhost/images/zone_lab.jpg")
                self.save_crop(im0, crop_arr, 'lab')
                # save_img = im0
                # if len(crop_arr) > 0:
                #     save_img = crop_arr[-1]
                # cv2.imwrite("C:\Apache24\htdocs\images\zone_lab.jpg", save_img)
            if self.counter3.in_counts_update or self.counter3.out_counts_update:
                self.post_event('b', 'in')
                self.post_save('b', 'save_image',"http://localhost/images/zone_b.jpg")
                self.save_crop(im0, crop_arr, 'b')
                # save_img = im0
                # if len(crop_arr) > 0:
                #     save_img = crop_arr[-1]
                # cv2.imwrite("C:\Apache24\htdocs\images\zone_b.jpg", save_img)
            # if self.counter4.in_counts_update:
            #     self.post_event('a', 'in')
            #     self.post_save('a', 'save_image',"http://localhost/images/zone_a.jpg")
            #     self.save_crop(im0, crop_arr, 'a')
            #     # save_img = im0
            #     # if len(crop_arr) > 0:
            #     #     save_img = crop_arr[-1]
            #     # cv2.imwrite("C:\Apache24\htdocs\images\zone_a.jpg", save_img)
            # if self.counter4.out_counts_update:
            #     self.post_event('a', 'out')
            #     self.post_save('a', 'save_image',"http://localhost/images/zone_a.jpg")
            #     self.save_crop(im0, crop_arr, 'a')
            #     # save_img = im0
            #     # if len(crop_arr) > 0:
            #     #     save_img = crop_arr[-1]
            #     # cv2.imwrite("C:\Apache24\htdocs\images\zone_a.jpg", save_img)

        else:
            counts = self.counter.in_counts + self.counter.out_counts
            msg = {'line_1': (counts, self.counter.in_counts, self.counter.out_counts)}

            event = ""
            if "-out" in self.camera_name:
                event = 'out'
            elif "-in" in self.camera_name:
                event = 'in'
            
            if "b-out" in self.camera_name:
                txt = cam + ": i={}, o={}".format(self.counter.out_counts, self.counter.in_counts)
            else:
                txt = cam + ": i={}, o={}".format(self.counter.in_counts, self.counter.out_counts)
            update.append(txt)
            if self.counter.in_counts_update or self.counter.out_counts_update:
                self.post_event(cam, event)
                # filePath = "C:\Apache24\htdocs\images\zone_" + cam + ".jpg"
                self.post_save(cam, 'save_image',"http://localhost/images/zone_" + str(cam) + ".jpg")
                # save_img = im0
                # if len(crop_arr) > 0:
                #     save_img = crop_arr[-1]
                # cv2.imwrite(filePath, save_img)

                self.save_crop(im0, crop_arr, cam)
        return msg, update

    def save_crop(self, img, obj, zone):
        save_img = img
        if zone in obj:
            save_img = obj[zone]
        # if len(obj) > 0:
        #     save_img = obj[-1]
        cv2.imwrite("C:\Apache24\htdocs\images\zone_{}.jpg".format(zone), save_img)

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
        self.bLoop=False
        self.video_writer.release()
        self.videocapture.release()
        cv2.destroyAllWindows()

    def run(self, stop_event):
        """Start the vehicle counting process."""
        collect_thread = threading.Thread(target=self.collect_images)
        process_thread = threading.Thread(target=self.process_images)

        collect_thread.start()
        process_thread.start()

        collect_thread.join()
        process_thread.join()
