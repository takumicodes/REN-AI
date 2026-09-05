import cv2
import os
from datetime import datetime

def capture_camera_frame(save_path="camera_capture.jpg"):
    """
    Captures a single frame from the default system camera and saves it to a file.
    This allows Ren to 'see' the current environment by capturing an image 
    which can then be analyzed by a vision model.
    """
    try:
        # Initialize the camera (0 is usually the default webcam)
        cam = cv2.VideoCapture(0)
        
        if not cam.isOpened():
            return {"status": "error", "message": "Could not access the camera. Please check if it is connected or used by another app."}

        # Allow the camera to warm up/adjust exposure
        # Read a few frames to ensure the image isn't dark/blurry
        for _ in range(5):
            cam.read()

        # Capture a single frame
        ret, frame = cam.read()

        if ret:
            # Generate a timestamped filename to avoid overwriting if desired, 
            # but for a 'current view' skill, a static name is often easier.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            full_path = os.path.join(os.getcwd(), filename)
            
            # Save the image
            cv2.imwrite(full_path, frame)
            
            # Release the camera
            cam.release()
            
            return {
                "status": "success", 
                "message": f"Image captured successfully.", 
                "file_path": full_path
            }
        else:
            cam.release()
            return {"status": "error", "message": "Failed to retrieve frame from camera."}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# Example usage for the agent:
if __name__ == "__main__":
    result = capture_camera_frame()
    print(result)