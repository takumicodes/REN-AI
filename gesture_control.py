import cv2
import mediapipe as mp
import pyautogui
import threading
import time


class GestureController:
    def __init__(self):
        self.running = False
        self.enabled = False

        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        # Stability
        self.current_gesture = None
        self.frame_count = 0
        self.stable_frames_required = 6

        # Edge trigger memory
        self.last_executed_gesture = None

    # ---------------------------------
    # Finger Detection
    # ---------------------------------
    def fingers_up(self, hand_landmarks):
        lm = hand_landmarks.landmark
        fingers = []

        # Thumb (frame flipped)
        if lm[4].x < lm[3].x:
            fingers.append(1)
        else:
            fingers.append(0)

        tips = [8, 12, 16, 20]
        for tip in tips:
            if lm[tip].y < lm[tip - 2].y:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    # ---------------------------------
    # Gesture Classification
    # ---------------------------------
    def detect_gesture(self, hand_landmarks):
        fingers = self.fingers_up(hand_landmarks)
        total = sum(fingers)
        

        if total == 0:
            return "fist"
        elif total == 5:
            return "palm"
        elif total == 4:
            return "four"
        elif total == 1 and fingers[1] == 1:
            return "one"
        elif total == 2 and fingers[1] == 1 and fingers[2] == 1:
            return "two"
        elif total == 3:
            return "three"
        return None

    # ---------------------------------
    # Action Logic (Edge Triggered)
    # ---------------------------------
    def execute_gesture(self, gesture):
        previous_gesture = None
        if gesture == self.last_executed_gesture:
            return  # Prevent repeat while still holding

        # Enable system
        if gesture == "three" and not self.enabled:
            
            self.enabled = True
            print("System ENABLED")
            

        # Disable system
        elif gesture == "four" and self.enabled:
            self.enabled = False
            print("System DISABLED")

        elif self.enabled:
            if gesture == "fist" and previous_gesture == None:
                previous_gesture = gesture
                print(previous_gesture)
                pyautogui.hotkey("win", "d")
                

            elif gesture == "palm" and previous_gesture != gesture:
                print(previous_gesture)
                pyautogui.hotkey("win", "d")
                

            elif gesture == "one":
                pyautogui.press("volumeup")

            elif gesture == "two":
                pyautogui.press("volumedown")
            
           

        self.last_executed_gesture = gesture
        
        
     # ---------------------------------
    # Main Loop
    # ---------------------------------
    def run(self):
        self.running = True
        cap = cv2.VideoCapture(0)

        # 1. Create a resizable window
        cv2.namedWindow("Gesture Debug", cv2.WINDOW_NORMAL)
        
        # 2. Set an initial default size (optional)
        cv2.resizeWindow("Gesture Debug", 800, 600)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)

            detected_gesture = None

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    detected_gesture = self.detect_gesture(hand_landmarks)

                    self.mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS
                    )

            # Stability check
            if detected_gesture == self.current_gesture:
                self.frame_count += 1
            else:
                self.current_gesture = detected_gesture
                self.frame_count = 0

            # Trigger only after stable detection
            if self.current_gesture and self.frame_count > self.stable_frames_required:
                self.execute_gesture(self.current_gesture)

            # Reset edge trigger if hand removed
            if detected_gesture is None:
                self.last_executed_gesture = None

            # UI
            status = "ON" if self.enabled else "OFF"
            cv2.putText(frame, f"System: {status}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 255, 0), 2)

            if detected_gesture:
                cv2.putText(frame, f"Gesture: {detected_gesture}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            # Because WINDOW_NORMAL is set, the frame will auto-stretch to the window size
            cv2.imshow("Gesture Debug", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.running = False

        cap.release()
        cv2.destroyAllWindows()



    # ---------------------------------
    # Thread Control
    # ---------------------------------
    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    def stop(self):
        self.running = False
    