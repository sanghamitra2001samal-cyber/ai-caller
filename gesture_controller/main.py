import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time

# Disable fail-safe to prevent accidental crashes if mouse hits corner
# Or keep it enabled for safety. Let's keep it but handle exceptions if needed.
pyautogui.FAILSAFE = False

class HandController:
    def __init__(self):
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Camera setup
        self.wCam, self.hCam = 640, 480
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, self.wCam)
        self.cap.set(4, self.hCam)
        
        # Screen setup
        self.wScr, self.hScr = pyautogui.size()
        self.frameR = 100 # Frame Reduction (margin)
        
        # Smoothing
        self.smoothening = 5
        self.plocX, self.plocY = 0, 0
        self.clocX, self.clocY = 0, 0
        
        # Click state to avoid multiple clicks
        self.last_click_time = 0
        self.click_cooldown = 0.5 # seconds

    def run(self):
        print("Starting Gesture Controller...")
        print("Press 'q' to quit.")
        
        while True:
            success, img = self.cap.read()
            if not success:
                print("Failed to capture image")
                break
            
            # Flip image for mirror view
            img = cv2.flip(img, 1)
            
            # Convert to RGB
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            results = self.hands.process(imgRGB)
            
            if results.multi_hand_landmarks:
                for handLms in results.multi_hand_landmarks:
                    self.process_hand(handLms, img)
                    # Only process first hand
                    self.mp_draw.draw_landmarks(img, handLms, self.mp_hands.HAND_CONNECTIONS)
                    break 
            
            cv2.imshow("Gesture Controller", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        cv2.destroyAllWindows()

    def process_hand(self, handLms, img):
        lmList = []
        h, w, c = img.shape
        
        for id, lm in enumerate(handLms.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            lmList.append([id, cx, cy])
            
        if len(lmList) != 0:
            # Index Finger Tip (ID 8)
            x1, y1 = lmList[8][1], lmList[8][2]
            # Thumb Tip (ID 4)
            x2, y2 = lmList[4][1], lmList[4][2]
            
            # Draw visual feedback area
            cv2.rectangle(img, (self.frameR, self.frameR), 
                         (self.wCam - self.frameR, self.hCam - self.frameR), 
                         (255, 0, 255), 2)
            
            # Map coordinates
            # np.interp maps the value from range [frameR, wCam-frameR] to [0, wScr]
            x3 = np.interp(x1, (self.frameR, self.wCam - self.frameR), (0, self.wScr))
            y3 = np.interp(y1, (self.frameR, self.hCam - self.frameR), (0, self.hScr))
            
            # Smoothen Values
            self.clocX = self.plocX + (x3 - self.plocX) / self.smoothening
            self.clocY = self.plocY + (y3 - self.plocY) / self.smoothening
            
            # Move Mouse
            try:
                pyautogui.moveTo(self.clocX, self.clocY)
            except Exception as e:
                pass
                
            self.plocX, self.plocY = self.clocX, self.clocY
            
            # Click logic
            length = np.hypot(x2 - x1, y2 - y1)
            
            # Visual feedback for distance
            cx_mid, cy_mid = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.circle(img, (cx_mid, cy_mid), 5, (255, 0, 0), cv2.FILLED)
            
            # Click Threshold
            if length < 40:
                cv2.circle(img, (cx_mid, cy_mid), 15, (0, 255, 0), cv2.FILLED)
                current_time = time.time()
                if current_time - self.last_click_time > self.click_cooldown:
                    pyautogui.click()
                    self.last_click_time = current_time

if __name__ == "__main__":
    app = HandController()
    app.run()
