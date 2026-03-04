import cv2
import time

def run_face_lock():

    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return False

    # Fullscreen window
    cv2.namedWindow("Face Lock", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Face Lock",
                          cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)

    verified = False
    start_time = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # Draw rectangle (optional, remove if you don’t want)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        if len(faces) > 0:
            if start_time is None:
                start_time = time.time()

            if time.time() - start_time > 2:
                verified = True
        else:
            start_time = None

        cv2.imshow("Face Lock", frame)

        if verified:
            cv2.waitKey(500)   # small delay before closing
            break

        if cv2.waitKey(1) & 0xFF == ord("q"): # Press Q to close forcefully
            break

    cap.release()
    cv2.destroyAllWindows()

    return verified