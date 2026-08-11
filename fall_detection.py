import cv2
import mediapipe as mp # type: ignore
import numpy as np
import time
import datetime
import requests

# ---------------------------------------------------------
# CONFIGURATION & SECRETS (Replace with your own or use .env)
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'  # Put your bot token here
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID_HERE'        # Put your chat id here
ALERT_COOLDOWN_SECONDS = 60                          # Cooldown set to 60 seconds
last_alert_time = 0

# MediaPipe Pose Initialization
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

def send_telegram_alert_with_photo(image_path, timestamp_str):
    """
    Sends an emergency alert photo along with the exact timestamp 
    to the designated Telegram chat via Telegram Bot API.
    """
    global last_alert_time
    current_time = time.time()

    # Check if the cooldown period has passed to prevent notification spam
    if current_time - last_alert_time > ALERT_COOLDOWN_SECONDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        caption = f"🚨 EMERGENCY ALERT: Fall detected!\n⏰ Time: {timestamp_str}"
        
        try:
            with open(image_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
                response = requests.post(url, data=data, files=files)
                
            if response.status_code == 200:
                print(f"[+] Telegram Alert with Photo Sent Successfully at {timestamp_str}!")
            else:
                print(f"[-] Failed to send Telegram alert. Response: {response.text}")
                
            last_alert_time = current_time
        except Exception as e:
            print(f"[-] Error sending Telegram alert: {e}")
    else:
        print("[i] Alert skipped due to 60-second cooldown period.")

# Initialize Video Capture (0 for default webcam, or RTSP stream URL for IP cameras)
cap = cv2.VideoCapture(0)
fall_frame_count = 0
ALERT_THRESHOLD = 20  # Number of continuous frames required to confirm a fall

print("Starting Advanced Mathematical Fall Detection System... Press 'q' to exit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Camera frame not accessible or stream ended.")
        break

    frame_height, frame_width, _ = frame.shape
    
    # Convert BGR frame to RGB for MediaPipe processing
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    is_fallen = False

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        
        # Extract coordinates for shoulders and hips
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * frame_width,
                           landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * frame_height]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * frame_width,
                            landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * frame_height]
        
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * frame_width if 'file_width' in locals() else landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * frame_width,
                      landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * frame_height] # Simplified below
        
        # Proper extraction for hips
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * frame_width,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * frame_height]
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x * frame_width,
                     landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y * frame_height]
        
        # Calculate central positions
        shoulder_center = np.mean([left_shoulder, right_shoulder], axis=0)
        hip_center = np.mean([left_hip, right_hip], axis=0)
        
        # Mathematical Fall Detection Logic: Vertical vs Horizontal distance ratio
        delta_y = abs(shoulder_center[1] - hip_center[1])
        delta_x = abs(shoulder_center[0] - hip_center[0])
        
        # If horizontal span dominates vertical span, flag as potential fall
        if delta_y < (delta_x * 1.1):
            fall_frame_count += 1
            if fall_frame_count >= ALERT_THRESHOLD:
                is_fallen = True
        else:
            fall_frame_count = 0

        # Draw skeleton landmarks and connections on the frame
        mp_drawing.draw_landmarks(
            frame, 
            results.pose_landmarks, 
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
        )

    # Status handling and emergency triggering
    if is_fallen:
        status_text = "ALERT: FALL DETECTED!"
        color = (0, 0, 255)
        
        # Capture snapshot and timestamp of the event
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        snapshot_filename = "fall_snapshot.jpg"
        cv2.imwrite(snapshot_filename, frame)
        
        # Trigger Telegram alert function
        send_telegram_alert_with_photo(snapshot_filename, current_timestamp)
    else:
        status_text = "STATUS: NORMAL"
        color = (0, 255, 0)

    # Display real-time status overlay on video feed
    cv2.putText(frame, status_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.imshow("Advanced Mathematical Fall Detection", frame)

    # Exit loop on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()