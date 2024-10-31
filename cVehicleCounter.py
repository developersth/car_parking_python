import cv2
import numpy as np
from collections import defaultdict
from pathlib import Path
from ultralytics import YOLO, solutions
from ultralytics.utils.files import increment_path

# Utility imports
from shapely.geometry import Polygon
from shapely.geometry.point import Point

track_history = defaultdict(list)

class VehicleCounter:
    def __init__(
        self,
        camera_name,
        weights="yolov8n.pt",
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

        # Set line points based on the camera name
        self.line_points = self.get_line_points(camera_name)
        
        # Prepare the model
        self.model = YOLO(self.weights)
        self.model.to("cuda") if device == "0" else self.model.to("cpu")

        # Video properties
        self.videocapture = cv2.VideoCapture(self.source)
        self.frame_width = int(self.videocapture.get(3))
        self.frame_height = int(self.videocapture.get(4))
        self.fps = int(self.videocapture.get(5))
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # Define classes to track
        self.classes = [2, 5, 6, 7]  # Define your own classes here

        # Set desired width and height for output video
        self.new_width, self.new_height = self.calculate_new_size(width=1280, height=None)

        # Initialize video writer
        save_dir = Path(f"D:\\CarPark\\{camera_name}")
        save_dir.mkdir(parents=True, exist_ok=True)
        self.video_writer = cv2.VideoWriter(str(save_dir / f"{Path(source).stem}.mp4"), self.fourcc, self.fps, (self.new_width, self.new_height))

    def get_line_points(self, camera_name):
        """Define line points based on camera name."""
        line_points_dict = {
            "lab-out": [(100, 300), (1000, 600)],
            "b-out": [(575, 275), (1280, 425)],
            "mg": [(250, 410), (1100, 400)],
            "b-in": [(50, 400), (500, 250)]
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

    def run(self):
        """Run the vehicle counting process on video frames."""
        counter = solutions.ObjectCounter(
            names=self.model.model.names,
            view_img=False,
            reg_pts=self.line_points,
            draw_tracks=True,
            line_thickness=self.line_thickness,
            view_in_counts=False,
            view_out_counts=False,
        )

        if self.camera_name == "b-in":
            counter2 = solutions.ObjectCounter(
                names=self.model.model.names,
                view_img=False,
                reg_pts=[(750, 200), (1050, 190)],
                draw_tracks=True,
                line_thickness=self.line_thickness,
                view_in_counts=False,
                view_out_counts=False,
            )

        vid_frame_count = 0
        while self.videocapture.isOpened():
            success, im0 = self.videocapture.read()
            if not success:
                print("Video frame is empty or video processing has been successfully completed.")
                break

            # Resize frame
            vid_frame_count += 1
            im0 = cv2.resize(im0, (self.new_width, self.new_height))

            # Track objects
            tracks = self.model.track(im0, persist=True, show=False, classes=self.classes, verbose=True)

            # Count and display counts
            im0 = counter.start_counting(im0, tracks)
            if self.camera_name == "b-in":
                counter2.start_counting(im0, tracks)
                cv2.putText(im0, f'In:{counter.in_counts}, Out:{counter2.in_counts}', (525, 225), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)
            else:
                cv2.putText(im0, f'In:{counter.in_counts}, Out:{counter.out_counts}', (525, 225), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)

            # Write frame to video
            self.video_writer.write(im0)

            # Display video frame if enabled
            if self.view_img:
                if vid_frame_count == 1:
                    cv2.namedWindow("Car counting")
                cv2.imshow("Car counting", im0)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        self.cleanup()

    def cleanup(self):
        """Release resources."""
        self.video_writer.release()
        self.videocapture.release()
        cv2.destroyAllWindows()

# Example usage
counter = VehicleCounter(camera_name="b-in", source="D:\\CarPark\\ZONE B-IN\\Camera1_VR-20241025-110855.mp4", view_img=True, save_img=True)
counter.run()
