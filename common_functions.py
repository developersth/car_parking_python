import cv2
from datetime import datetime
import numpy as np

def crop_object(image, box, margin=0.5):
    """
    Crop an object from an image based on a bounding box and apply a margin for aesthetics.

    Parameters:
        image (numpy.ndarray): The input image.
        box (list or tuple): Bounding box in the format [x_min, y_min, x_max, y_max].
        margin (float): Margin as a fraction of the box dimensions (default: 0.1).

    Returns:
        numpy.ndarray: The cropped object image.
    """
    (h, w) = image.shape[:2]

    # Unpack the bounding box
    x_min, y_min, x_max, y_max = box

    # Calculate the width and height of the bounding box
    box_width = x_max - x_min
    box_height = y_max - y_min

    # Apply margin
    margin_x = int(margin * box_width)
    margin_y = int(margin * box_height)

    # Calculate new crop boundaries with margin
    x_min = max(0, int(x_min - margin_x))
    y_min = max(0, int(y_min - margin_y))
    x_max = min(w, int(x_max + margin_x))
    y_max = min(h, int(y_max + margin_y))

    # Crop the image
    # print([y_min, y_max, x_min, x_max])
    cropped = image[y_min:y_max, x_min:x_max]
    return cropped

def fill_area_with_mask(image, points):
    # Check if the points are sufficient to form a polygon
    if len(points) < 3:
        print("Error: At least 3 points are required to create a polygon.")
        return image  # Return the original image if not enough points
    
    # Convert points to numpy array of shape (n_points, 1, 2) for OpenCV
    pts = np.array(points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    
    # Create a mask with the same dimensions as the image
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    # Fill the area defined by points with white color on the mask
    cv2.fillPoly(mask, [pts], 255)
    
    # Use the mask to set the area in the image to black
    image[mask == 255] = [0, 0, 0]
    
    return image

def calculate_total_distance(points):
    # Initialize total distance
    total_distance = 0.0
    
    # Iterate through the points and calculate the distance between consecutive points
    for i in range(1, len(points)):
        # Get the current point and the previous point
        point1 = points[i-1][0]
        point2 = points[i][0]
        
        # Calculate Euclidean distance between the points
        distance = np.linalg.norm(np.array(point2) - np.array(point1))
        
        # Add to the total distance
        total_distance += distance
    
    return total_distance

def calculate_new_size(width=None, height=None, original_width=None, original_height=None):
    if width is None and height is None:
        raise ValueError("At least one of width or height must be provided")

    # Determine new dimensions
    if width is None:
        # Calculate the new width based on height
        ratio = height / float(original_height)
        new_width = int(original_width * ratio)
        new_height = height
    elif height is None:
        # Calculate the new height based on width
        ratio = width / float(original_width)
        new_width = width
        new_height = int(original_height * ratio)
    else:
        # Calculate the ratio of width and height to maintain aspect ratio
        ratio_width = width / float(original_width)
        ratio_height = height / float(original_height)
        ratio = min(ratio_width, ratio_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
    
    return (new_width, new_height)

def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    dim = calculate_new_size(width=width, height=height, original_width=w, original_height=h)

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized

def get_date_time_string():
    # Get the current date and time
    now = datetime.now()
    
    # Format it as a string (e.g., "2024-08-15 13:45:30")
    formatted_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    
    return formatted_string

def crop_image(image, x, y, w, h, output_name, timestamp):
    # Crop the image using the provided x, y, width (w), and height (h)
    cropped_image = image[y:y+h, x:x+w]
    
    # Save the cropped image to the specified output path
    cv2.imwrite("images/"+timestamp+"_"+output_name+".png", cropped_image)
    
    return cropped_image

def format_to_three_digits(number):
    # Format the number to a string with leading zeros (up to 3 digits)
    return f"{number:03}"
