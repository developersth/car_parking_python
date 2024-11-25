import cv2
import os

def reduce_frame_rate_and_resize(input_video_path, output_video_path, target_fps=10, target_width=640):
    # Open the input video file
    cap = cv2.VideoCapture(input_video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file {input_video_path}")
        return

    # Get the original video's properties
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Original FPS: {original_fps}, Original Width: {original_width}, Original Height: {original_height}")
    print(f"Total Frames: {total_frames}")

    if original_width == 0 or original_height == 0:
        print("Error: Could not retrieve video dimensions.")
        cap.release()
        return

    # Calculate the new height while maintaining the aspect ratio
    target_height = int(original_height * (target_width / original_width))

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, target_fps, (target_width, target_height))

    frame_count = 0
    processed_frames = 0
    skip_frames = int(original_fps / target_fps) - 1

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % (skip_frames + 1) == 0:
            # Resize the frame
            resized_frame = cv2.resize(frame, (target_width, target_height))

            # Write the frame to the output video
            out.write(resized_frame)

            # processed_frames += 1
            print(f"Processing: {frame_count}/{total_frames}")

        frame_count += 1

    # Release everything when the job is finished
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Processing complete for {input_video_path}.")

def process_all_videos_in_folder(input_folder, output_folder, target_fps=10, target_width=640):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Iterate over all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".MP4") or filename.endswith(".mp4") or filename.endswith(".avi") or filename.endswith(".mov"):
            input_video_path = os.path.join(input_folder, filename)
            output_video_path = os.path.join(output_folder, f"reduce_{filename}")
            reduce_frame_rate_and_resize(input_video_path, output_video_path, target_fps, target_width)

if __name__ == "__main__":
    # input_folder = 'C:\\Users\\surachair\\Downloads\\Filemail.com - TOP-MarineVideo2'
    # output_folder = 'C:\\Users\\surachair\\Downloads\\Filemail.com - TOP-MarineVideo2\\Processed'
    # process_all_videos_in_folder(input_folder, output_folder)

    input_video_path = "D:\\CarPark\\rtsp\\cam_a\\20241123_101017.mp4"
    output_video_path = "D:\\CarPark\\rtsp\\reduce_cam_a_20241123_101017.mp4"
    target_fps=10
    target_width=640
    reduce_frame_rate_and_resize(input_video_path, output_video_path, target_fps, target_width)
