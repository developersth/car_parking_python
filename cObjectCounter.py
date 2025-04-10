# Ultralytics YOLO 🚀, AGPL-3.0 license

from collections import defaultdict

import cv2

from ultralytics.utils.checks import check_imshow, check_requirements
from ultralytics.utils.plotting import Annotator, colors

check_requirements("shapely>=2.0.0")

from shapely.geometry import LineString, Point, Polygon
from common_functions import *


class cObjectCounter:
    """A class to manage the counting of objects in a real-time video stream based on their tracks."""

    def __init__(
        self,
        names,
        reg_pts=None,
        line_thickness=2,
        view_img=False,
        view_in_counts=True,
        view_out_counts=True,
        draw_tracks=False,
    ):
        """
        Initializes the ObjectCounter with various tracking and counting parameters.

        Args:
            names (dict): Dictionary of class names.
            reg_pts (list): List of points defining the counting region.
            line_thickness (int): Line thickness for bounding boxes.
            view_img (bool): Flag to control whether to display the video stream.
            view_in_counts (bool): Flag to control whether to display the in counts on the video stream.
            view_out_counts (bool): Flag to control whether to display the out counts on the video stream.
            draw_tracks (bool): Flag to control whether to draw the object tracks.
        """
        # Mouse events
        self.is_drawing = False
        self.selected_point = None

        # Region & Line Information
        self.reg_pts = [(20, 400), (1260, 400)] if reg_pts is None else reg_pts
        self.counting_region = None

        # Image and annotation Information
        self.im0 = None
        self.tf = line_thickness
        self.view_img = view_img
        self.view_in_counts = view_in_counts
        self.view_out_counts = view_out_counts

        self.names = names  # Classes names
        self.window_name = "Ultralytics YOLOv8 Object Counter"

        # Object counting Information
        self.state = ""
        self.in_counts = 0
        self.out_counts = 0
        self.in_counts_update = False
        self.out_counts_update = False
        self.count_ids = []
        self.class_wise_count = {}

        # Tracks info
        self.track_history = defaultdict(list)
        self.draw_tracks = draw_tracks

        # Check if environment supports imshow
        self.env_check = check_imshow(warn=True)

        # Initialize counting region
        if len(self.reg_pts) == 2:
            print("Line Counter Initiated.")
            self.counting_region = LineString(self.reg_pts)
        elif len(self.reg_pts) >= 3:
            print("Polygon Counter Initiated.")
            self.counting_region = Polygon(self.reg_pts)
        else:
            print("Invalid Region points provided, region_points must be 2 for lines or >= 3 for polygons.")
            print("Using Line Counter Now")
            self.counting_region = LineString(self.reg_pts)

        # Define the counting line segment
        self.counting_line_segment = LineString(
            [
                (self.reg_pts[0][0], self.reg_pts[0][1]),
                (self.reg_pts[1][0], self.reg_pts[1][1]),
            ]
        )

    def mouse_event_for_region(self, event, x, y, flags, params):
        """
        Handles mouse events for defining and moving the counting region in a real-time video stream.

        Args:
            event (int): The type of mouse event (e.g., cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONDOWN, etc.).
            x (int): The x-coordinate of the mouse pointer.
            y (int): The y-coordinate of the mouse pointer.
            flags (int): Any associated event flags (e.g., cv2.EVENT_FLAG_CTRLKEY,  cv2.EVENT_FLAG_SHIFTKEY, etc.).
            params (dict): Additional parameters for the function.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, point in enumerate(self.reg_pts):
                if (
                    isinstance(point, (tuple, list))
                    and len(point) >= 2
                    and (abs(x - point[0]) < 10 and abs(y - point[1]) < 10)
                ):
                    self.selected_point = i
                    self.is_drawing = True
                    break

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_drawing and self.selected_point is not None:
                self.reg_pts[self.selected_point] = (x, y)
                self.counting_region = Polygon(self.reg_pts)

        elif event == cv2.EVENT_LBUTTONUP:
            self.is_drawing = False
            self.selected_point = None

    def extract_and_process_tracks(self, tracks, track_algorithms="centroid"):
        prev_in_count = self.in_counts
        prev_out_count = self.out_counts
        self.in_counts_update = False
        self.out_counts_update = False
        detect_img = None

        """Extracts and processes tracks for object counting in a video stream."""
        # Annotator Init and region drawing
        annotator = Annotator(self.im0, self.tf, self.names)

        # Draw region or line
        annotator.draw_region(reg_pts=self.reg_pts, color=(104, 0, 123), thickness=self.tf * 2)

        # Extract tracks for OBB or object detection
        track_data = tracks[0].obb or tracks[0].boxes
        # print(track_data.cls)
        # print("start......")
        # print(track_data.conf)
        # print("=========")
        # print(track_data)
        # print("end......")
        if track_data:
            boxes = track_data.xyxy.cpu()
            clss = track_data.cls.cpu().tolist()
            confs = track_data.conf.cpu().tolist()
            for box, cls, conf in zip(boxes, clss, confs):
                # Draw bounding box
                txt = self.names[cls] + "," + str(round(conf,2))
                # print(txt)
                annotator.box_label(box, label=txt)

        if track_data and track_data.id is not None:
            # print('xxxxxxxxxxxxxxxxxxxxx')
            boxes = track_data.xyxy.cpu()
            clss = track_data.cls.cpu().tolist()
            track_ids = track_data.id.int().cpu().tolist()

            # Extract tracks
            for box, track_id, cls in zip(boxes, track_ids, clss):
                if cls in [2, 5, 6, 7]:
                    cls = 2

                # Draw bounding box
                annotator.box_label(box, label=self.names[cls], color=colors(int(track_id), True))

                # Store class info
                if self.names[cls] not in self.class_wise_count:
                    self.class_wise_count[self.names[cls]] = {"IN": 0, "OUT": 0}

                # Draw Tracks
                track_line = self.track_history[track_id]
                # print(track_algorithms)
                if track_algorithms == None or track_algorithms == "centroid":
                    track_line.append((float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2)))
                elif track_algorithms == "buttom-right":
                    track_line.append((float(box[2]), float(box[3])))
                elif track_algorithms == "buttom-center":
                    track_line.append((float((box[0] + box[2]) / 2), float(box[3])))
                elif track_algorithms == "center-right":
                    track_line.append( (float(box[2]), float((box[1] + box[3]) / 2)) )
                if len(track_line) > 150:
                    track_line.pop(0)

                # Draw track trails
                if self.draw_tracks:
                    annotator.draw_centroid_and_tracks(
                        track_line,
                        color=colors(int(track_id), True),
                        track_thickness=self.tf,
                    )

                # prev_position = self.track_history[track_id][-2] if len(self.track_history[track_id]) > 1 else None
                if len(self.track_history[track_id]) >= 5:
                    prev_position = self.track_history[track_id][-5]
                elif len(self.track_history[track_id]) > 1:
                    prev_position = self.track_history[track_id][-len(self.track_history[track_id])]
                else:
                    prev_position = None

                # Count objects in any polygon
                if len(self.reg_pts) >= 3:
                    is_inside = self.counting_region.contains(Point(track_line[-1]))

                    if prev_position is not None and is_inside and track_id not in self.count_ids:
                        self.count_ids.append(track_id)

                        if (box[0] - prev_position[0]) * (self.counting_region.centroid.x - prev_position[0]) > 0:
                            self.in_counts += 1
                            self.class_wise_count[self.names[cls]]["IN"] += 1
                        else:
                            self.out_counts += 1
                            self.class_wise_count[self.names[cls]]["OUT"] += 1

                # Count objects using line
                elif len(self.reg_pts) == 2:
                    if ( prev_position is not None and track_id not in self.count_ids ):
                        # Check if the object's movement segment intersects the counting line
                        line_coords = list(self.counting_line_segment.coords)
                        direction = self.check_crossing_within_line_area(line_coords[0], line_coords[1], (prev_position[0], prev_position[1]), track_line[-1])

                        if direction == "IN" or direction == "OUT":
                            self.count_ids.append(track_id)
                            detect_img = crop_object(self.im0, box)
                            # print("direction: ", direction)

                            # Determine the direction of movement (IN or OUT)
                            # dx = (box[0] - prev_position[0]) * (self.counting_region.centroid.x - prev_position[0])
                            # dy = (box[1] - prev_position[1]) * (self.counting_region.centroid.y - prev_position[1])
                            # if dx > 0 and dy > 0:
                            if direction == "IN":
                                self.in_counts += 1
                                self.class_wise_count[self.names[cls]]["IN"] += 1
                                self.state = "IN"
                            # else:
                            elif direction == "OUT":
                                self.out_counts += 1
                                self.class_wise_count[self.names[cls]]["OUT"] += 1
                                self.state = "OUT"
                        # else:
                        #     print("direction: ", direction)

        labels_dict = {}

        for key, value in self.class_wise_count.items():
            if value["IN"] != 0 or value["OUT"] != 0:
                if not self.view_in_counts and not self.view_out_counts:
                    continue
                elif not self.view_in_counts:
                    labels_dict[str.capitalize(key)] = f"OUT {value['OUT']}"
                elif not self.view_out_counts:
                    labels_dict[str.capitalize(key)] = f"IN {value['IN']}"
                else:
                    labels_dict[str.capitalize(key)] = f"IN {value['IN']} OUT {value['OUT']}"

        if labels_dict:
            annotator.display_analytics(self.im0, labels_dict, (104, 31, 17), (255, 255, 255), 10)
        
        if prev_in_count != self.in_counts:
            self.in_counts_update = True
        if prev_out_count != self.out_counts:
            self.out_counts_update = True
        
        return detect_img

    def check_crossing_within_line_area(self, line_start, line_end, prev_point, curr_point):
        """
        Checks if the last two points crossed the line segment defined by line_start and line_end
        and if both points are within the area of the line segment.
        """
        # Convert the points to Point objects
        prev_pt = Point(prev_point)
        curr_pt = Point(curr_point)

        # Check if both points are within the bounding box of the line segment
        # if not (self.is_point_in_segment_area(prev_pt, line_start, line_end) and
        #         self.is_point_in_segment_area(curr_pt, line_start, line_end)):
        if not self.is_point_in_segment_area(curr_pt, line_start, line_end):
            return "No crossing (points not in line area)"

        # Use the cross product check for crossing direction
        return self.check_direction_cross_product(line_start, line_end, prev_point, curr_point)

    def is_point_in_segment_area(self, point, line_start, line_end):
        """
        Checks if the given point is within the bounding box defined by line_start and line_end.
        """
        min_x = min(line_start[0], line_end[0])
        max_x = max(line_start[0], line_end[0])
        min_y = min(line_start[1], line_end[1])
        max_y = max(line_start[1], line_end[1])

        return min_x <= point.x <= max_x and min_y <= point.y <= max_y

    def check_direction_cross_product(self, line_start, line_end, prev_point, curr_point):
        # Convert LineString to start and end points
        #line_start, line_end = line.coords[0], line.coords[-1]

        # Create points for previous and current centroid positions
        prev_pt = Point(prev_point)
        curr_pt = Point(curr_point)

        # Calculate vectors
        v_line = (line_end[0] - line_start[0], line_end[1] - line_start[1])
        v_prev = (prev_pt.x - line_start[0], prev_pt.y - line_start[1])
        v_curr = (curr_pt.x - line_start[0], curr_pt.y - line_start[1])

        # Calculate cross products
        cross_prev = v_line[0] * v_prev[1] - v_line[1] * v_prev[0]  # Cross product for previous point
        cross_curr = v_line[0] * v_curr[1] - v_line[1] * v_curr[0]  # Cross product for current point

        # Check for crossing
        if cross_prev * cross_curr < 0:
            return "OUT" if cross_curr > 0 else "IN"

        return "No crossing"

    def display_frames(self):
        """Displays the current frame with annotations and regions in a window."""
        if self.env_check:
            cv2.namedWindow(self.window_name)
            if len(self.reg_pts) == 4:  # only add mouse event If user drawn region
                cv2.setMouseCallback(self.window_name, self.mouse_event_for_region, {"region_points": self.reg_pts})
            cv2.imshow(self.window_name, self.im0)
            # Break Window
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return

    def start_counting(self, im0, tracks, track_algorithms="centroid", parent_name=""):
        """
        Main function to start the object counting process.

        Args:
            im0 (ndarray): Current frame from the video stream.
            tracks (list): List of tracks obtained from the object tracking process.
        """
        if parent_name != "":
            print("parent_name: ", parent_name)
        self.im0 = im0  # store image
        detect_img = self.extract_and_process_tracks(tracks, track_algorithms)  # draw region even if no objects

        if self.view_img:
            self.display_frames()
        return self.im0, detect_img


if __name__ == "__main__":
    classes_names = {0: "person", 1: "car"}  # example class names
    cObjectCounter(classes_names)
