import cv2
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    print("CUDA is enabled and GPU is available.")
else:
    print("CUDA is not enabled or no GPU is found.")