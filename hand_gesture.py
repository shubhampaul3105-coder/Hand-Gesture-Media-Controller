import ctypes
import math
import time
import cv2
import mediapipe as mp
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
def send_windows_key(vk_code: int):
    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[Error] Failed to send key event: {e}")
class GestureRecognizer:
    @staticmethod
    def dist_2d(p1, p2) -> float:
        return math.hypot(p1.x - p2.x, p1.y - p2.y)
    @staticmethod
    def dist_3d(p1, p2) -> float:
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)
    def is_finger_extended(self, tip_idx: int, pip_idx: int, landmarks) -> bool:
        wrist = landmarks[0]
        d_tip = self.dist_3d(landmarks[tip_idx], wrist)
        d_pip = self.dist_3d(landmarks[pip_idx], wrist)
        return d_tip > (d_pip * 1.15)
    def classify(self, landmarks) -> str:
        index_ext = self.is_finger_extended(8, 6, landmarks)
        middle_ext = self.is_finger_extended(12, 10, landmarks)
        ring_ext = self.is_finger_extended(16, 14, landmarks)
        pinky_ext = self.is_finger_extended(20, 18, landmarks)
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        if self.dist_2d(thumb_tip, landmarks[8]) < 0.065 and middle_ext and ring_ext and pinky_ext:
            return "OK_SIGN"
        if not index_ext and not middle_ext and not ring_ext and not pinky_ext and thumb_tip.y < thumb_ip.y - 0.03 and thumb_tip.y < thumb_mcp.y - 0.05 and thumb_tip.y < landmarks[5].y - 0.04:
            return "THUMBS_UP"
        if not index_ext and not middle_ext and not ring_ext and not pinky_ext and thumb_tip.y > thumb_ip.y + 0.03 and thumb_tip.y > thumb_mcp.y + 0.05 and thumb_tip.y > landmarks[5].y + 0.04:
            return "THUMBS_DOWN"
        thumb_extended = self.dist_2d(thumb_tip, thumb_mcp) > 0.08
        if index_ext and middle_ext and ring_ext and pinky_ext and thumb_extended:
            return "OPEN_PALM"
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            if self.dist_2d(landmarks[8], landmarks[12]) > 0.035:
                return "PEACE"
        if index_ext and not middle_ext and not ring_ext and not pinky_ext:
            return "POINT_UP"
        if not index_ext and not middle_ext and not ring_ext and not pinky_ext:
            return "FIST"
        return "UNKNOWN"
def draw_ui_overlay(frame, active_gesture: str, action_feedback: str, feedback_timer: float, fps: float):
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 85), (20, 24, 30), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    gesture_labels = {
        "THUMBS_UP": ("[+] THUMBS UP", (50, 220, 100)),
        "THUMBS_DOWN": ("[-] THUMBS DOWN", (80, 80, 255)),
        "OPEN_PALM": ("[||] OPEN PALM", (255, 200, 50)),
        "PEACE": ("[>>] PEACE SIGN", (255, 120, 50)),
        "POINT_UP": ("[<<] POINT UP", (200, 100, 255)),
        "OK_SIGN": ("[X] OK SIGN", (50, 220, 240)),
        "FIST": ("[#] FIST (IDLE)", (160, 160, 160)),
        "UNKNOWN": ("SEARCHING...", (120, 120, 120)),
    }
    label, color = gesture_labels.get(active_gesture, ("SEARCHING...", (120, 120, 120)))
    cv2.putText(frame, f"Gesture: {label}", (20, 42), cv2.FONT_HERSHEY_DUPLEX, 0.95, color, 2)
    if time.time() - feedback_timer < 1.2 and action_feedback:
        cv2.putText(frame, f"ACTION: {action_feedback}", (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    else:
        cv2.putText(frame, "Status: Ready", (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
    cv2.putText(frame, f"FPS: {int(fps)}", (w - 120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    sheet_w, sheet_h = 230, 220
    x1, y1 = 15, h - sheet_h - 15
    x2, y2 = x1 + sheet_w, h - 15
    box_overlay = frame.copy()
    cv2.rectangle(box_overlay, (x1, y1), (x2, y2), (25, 28, 35), -1)
    cv2.addWeighted(box_overlay, 0.7, frame, 0.3, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 90, 110), 1)
    instructions = [
        ("GESTURE CONTROLS", (255, 255, 255), 0.5, 2),
        ("Thumbs Up    : Vol Up", (50, 220, 100), 0.45, 1),
        ("Thumbs Down  : Vol Down", (80, 80, 255), 0.45, 1),
        ("Open Palm    : Play/Pause", (255, 200, 50), 0.45, 1),
        ("Peace (V)    : Next Track", (255, 120, 50), 0.45, 1),
        ("Point Up     : Prev Track", (200, 100, 255), 0.45, 1),
        ("OK Sign      : Mute/Unmute", (50, 220, 240), 0.45, 1),
        ("Closed Fist  : Standby", (160, 160, 160), 0.45, 1),
        ("Press 'q' to Exit", (130, 180, 230), 0.45, 1),
    ]
    curr_y = y1 + 24
    for text, col, scale, thickness in instructions:
        cv2.putText(frame, text, (x1 + 10, curr_y), cv2.FONT_HERSHEY_SIMPLEX, scale, col, thickness)
        curr_y += 21
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Could not open webcam.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    recognizer = GestureRecognizer()
    last_volume_time = 0.0
    last_action_time = 0.0
    action_feedback = ""
    feedback_timer = 0.0
    VOLUME_REPEAT_INTERVAL = 0.22
    ACTION_COOLDOWN = 1.30
    candidate_gesture = "UNKNOWN"
    gesture_hold_counter = 0
    REQUIRED_HOLD_FRAMES = 3
    active_gesture = "UNKNOWN"
    prev_time = time.time()
    fps = 30.0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            curr_time = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(curr_time - prev_time, 0.001))
            prev_time = curr_time
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = hands.process(rgb_frame)
            rgb_frame.flags.writeable = True
            detected_gesture = "UNKNOWN"
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )
                    detected_gesture = recognizer.classify(hand_landmarks.landmark)
            if detected_gesture == candidate_gesture and detected_gesture != "UNKNOWN":
                gesture_hold_counter += 1
            else:
                candidate_gesture = detected_gesture
                gesture_hold_counter = 1
            if gesture_hold_counter >= REQUIRED_HOLD_FRAMES:
                active_gesture = candidate_gesture
            else:
                if detected_gesture == "UNKNOWN":
                    active_gesture = "UNKNOWN"
            now = time.time()
            if active_gesture == "THUMBS_UP":
                if now - last_volume_time >= VOLUME_REPEAT_INTERVAL:
                    send_windows_key(VK_VOLUME_UP)
                    last_volume_time = now
                    action_feedback = "Volume UP (+2%)"
                    feedback_timer = now
            elif active_gesture == "THUMBS_DOWN":
                if now - last_volume_time >= VOLUME_REPEAT_INTERVAL:
                    send_windows_key(VK_VOLUME_DOWN)
                    last_volume_time = now
                    action_feedback = "Volume DOWN (-2%)"
                    feedback_timer = now
            elif active_gesture == "OPEN_PALM":
                if now - last_action_time >= ACTION_COOLDOWN:
                    send_windows_key(VK_MEDIA_PLAY_PAUSE)
                    last_action_time = now
                    action_feedback = "Play / Pause Toggle"
                    feedback_timer = now
            elif active_gesture == "PEACE":
                if now - last_action_time >= ACTION_COOLDOWN:
                    send_windows_key(VK_MEDIA_NEXT_TRACK)
                    last_action_time = now
                    action_feedback = "Next Track >>"
                    feedback_timer = now
            elif active_gesture == "POINT_UP":
                if now - last_action_time >= ACTION_COOLDOWN:
                    send_windows_key(VK_MEDIA_PREV_TRACK)
                    last_action_time = now
                    action_feedback = "Previous Track <<"
                    feedback_timer = now
            elif active_gesture == "OK_SIGN":
                if now - last_action_time >= ACTION_COOLDOWN:
                    send_windows_key(VK_VOLUME_MUTE)
                    last_action_time = now
                    action_feedback = "Mute / Unmute"
                    feedback_timer = now
            draw_ui_overlay(frame, active_gesture, action_feedback, feedback_timer, fps)
            cv2.imshow("Hand Gesture Media Controller (Press 'q' to Quit)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
if __name__ == "__main__":
    main()