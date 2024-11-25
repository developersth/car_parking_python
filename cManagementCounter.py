import sys
from pathlib import Path

# Remove the existing `ultralytics` module from sys.modules if already imported
if 'ultralytics' in sys.modules:
    del sys.modules['ultralytics']

# Insert the custom `ultralytics` path at the beginning of sys.path
sys.path.insert(0, r"D:\\ultralytics")

import cv2
import torch
from ultralytics import YOLO
import signal
import sys
import os
from common_functions import *

class cManagementCounter:
    def __init__(self, input_video_path, output_video_path, debug_video_path, model_path="yolov10s.pt", view_img=False):
        self.input_video_path = input_video_path
        self.output_video_path = output_video_path
        self.debug_video_path = debug_video_path
        self.view_img = view_img
        self.model = YOLO(model_path)
        self.count_history = []
        self.mask = []

        # if not os.path.exists(self.source):
        #     print("File {} is not exist.".format(str(self.source)))
        #     exit()

        # Open the video file
        self.cap = cv2.VideoCapture(self.input_video_path)
        if not self.cap.isOpened():
            print("Error: Could not open video.")
            sys.exit()

        # Get video properties
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.masks = [
            [(0, 0), 
             (0, int(self.frame_height*0.17)), 
             (int(self.frame_width), int(self.frame_height*0.18)), 
             (int(self.frame_width), 0)],
            [(int(self.frame_width*0.45), int(self.frame_height*0.17)),
             (int(self.frame_width*0.2), self.frame_height),
             (int(self.frame_width*0.75), self.frame_height),
             (int(self.frame_width*0.50), int(self.frame_height*0.17))],
            [(int(self.frame_width*0.60), int(self.frame_height*0.17)),
             (int(self.frame_width*0.90), int(self.frame_height*0.40)),
             (self.frame_width, int(self.frame_height*0.50)),
             (self.frame_width, int(self.frame_height*0.17))],
            [(0, int(self.frame_height*0.55)),
             (0, self.frame_height),
             (self.frame_width, self.frame_height),
             (self.frame_width, int(self.frame_height*0.55))],
                     ]

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(self.output_video_path, fourcc, self.fps, (self.frame_width, self.frame_height))
        self.out_debug = cv2.VideoWriter(self.debug_video_path, fourcc, self.fps, (self.frame_width, self.frame_height))

        # Register the signal handler for graceful exit
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        print("\nExiting gracefully...")
        self.release_resources()
        sys.exit(0)

    def process_frame(self, frame, debug_frame):
        # Perform object detection on the frame
        results = self.model(debug_frame)
        desired_classes = [2, 7]  # YOLO class IDs for 'car' and 'truck'
        count = 0

        # Draw filtered detections on the frame
        for detection in results[0].boxes:
            class_id = int(detection.cls)
            confidence = detection.conf
            x1, y1, x2, y2 = map(int, detection.xyxy[0])

            # Filter for cars and trucks and region filtering
            if class_id in desired_classes and ((x1 > 150 and x2 < self.frame_width / 2 and y1 > 20 and y2 < self.frame_height * 7.0 / 10.0) or 
                                                (x1 > self.frame_width / 2 and x2 < self.frame_width-100 and y1 > 20 and y2 < self.frame_height * 6.0 / 10.0)):
                # Draw bounding box
                cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Add label and confidence score
                label = str(self.model.names[class_id]) + " : " + str(confidence)
                cv2.putText(debug_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                count += 1

        # Maintain count history for averaging
        self.count_history.append(count)
        if len(self.count_history) > 1800:
            self.count_history.pop(0)
        count_avg = sum(self.count_history) / len(self.count_history)
        count_avg_int = int(round(count_avg))

        # Display average count on frame
        cv2.putText(debug_frame, f"Car: {count_avg_int}", (int(self.frame_width / 2 - 200), int(self.frame_height / 2 - 25)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 3)
        cv2.putText(frame, f"Car: {count_avg_int}", (int(self.frame_width / 2 - 200), int(self.frame_height / 2 - 25)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 3)
        
        return frame, debug_frame

    def process_video(self):
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            debug_frame = frame.copy()

            for mask in self.masks:
                # Apply the mask and fill the selected area in black
                debug_frame = fill_area_with_mask(debug_frame, mask)

            # Process the frame for object detection and counting
            processed_frame, debug_frame = self.process_frame(frame, debug_frame)

            # Write the processed frame to the output video
            self.out.write(processed_frame)
            self.out_debug.write(debug_frame)

            if self.view_img:
                # Optional: Display the frame (uncomment if running locally)
                resized_img = image_resize(processed_frame, width=640)
                cv2.imshow("YOLOv8 Detection", resized_img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    def release_resources(self):
        # Release all resources
        self.cap.release()
        self.out.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Path to your video file and output file
    input_video_path = "D:\\CarPark\\MG\\Camera4_VR-20241025-111430.mp4"  # change this to your input video path
    output_video_path = "output_video.mp4"

    # Create an instance of YOLOCarCounter and process the video
    car_counter = cManagementCounter(input_video_path, output_video_path)
    car_counter.process_video()
    car_counter.release_resources()
