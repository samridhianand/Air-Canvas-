import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import time
import math

# Initialize drawing canvas and colors
bpoints, gpoints, rpoints, ypoints = [deque(maxlen=1024) for _ in range(4)]
blue_index = green_index = red_index = yellow_index = 0
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255)]
colorIndex = 0
canvas_cleared = False  # Flag to track if canvas is cleared

# Create drawing canvas
paintWindow = np.ones((471, 636, 3), dtype=np.uint8) * 255
buttons = [
    {"label": "CLEAR", "coords": (40, 1, 140, 65)},
    {"label": "BLUE", "coords": (160, 1, 255, 65), "color": colors[0]},
    {"label": "GREEN", "coords": (275, 1, 370, 65), "color": colors[1]},
    {"label": "RED", "coords": (390, 1, 485, 65), "color": colors[2]},
    {"label": "YELLOW", "coords": (505, 1, 600, 65), "color": colors[3]},
]

# Initialize webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Setup MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

def draw_ui(frame):
    for btn in buttons:
        x1, y1, x2, y2 = btn["coords"]
        color = btn.get("color", (122, 122, 122))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.putText(
            frame,
            btn["label"],
            (x1 + 10, int((y1 + y2) / 2) + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255) if "color" in btn else (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

def distance(p1, p2):
    """Compute the Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

print("AirWhiteboard started. Press 'q' to quit.")
last_log_time = time.time()

drawing = False  # To track whether drawing is enabled or not
drawing_start_position = None  # Track the position where drawing starts

while True:
    success, frame = cap.read()
    if not success:
        print("⚠️ Frame capture failed, retrying...")
        continue

    frame = cv2.flip(frame, 1)
    draw_ui(frame)

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)

    center = None

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            x_thumb = int(hand_landmarks.landmark[4].x * frame.shape[1])
            y_thumb = int(hand_landmarks.landmark[4].y * frame.shape[0])
            x_index = int(hand_landmarks.landmark[8].x * frame.shape[1])
            y_index = int(hand_landmarks.landmark[8].y * frame.shape[0])
            x_middle = int(hand_landmarks.landmark[12].x * frame.shape[1])
            y_middle = int(hand_landmarks.landmark[12].y * frame.shape[0])

            # Calculate the distance between the thumb and index finger
            thumb_index_distance = distance((x_thumb, y_thumb), (x_index, y_index))
            thumb_middle_distance = distance((x_thumb, y_thumb), (x_middle, y_middle))

            # Define a threshold distance to detect pinch
            pinch_threshold = 50  # You can adjust this value as per your needs

            if thumb_index_distance < pinch_threshold or thumb_middle_distance < pinch_threshold:
                if not drawing:  # Start drawing if not already drawing
                    drawing = True
                    drawing_start_position = (x_index, y_index)  # Save the new start position
                    print("Drawing started")
            else:
                if drawing:  # Stop drawing when the pinch is no longer detected
                    drawing = False
                    print("Drawing stopped")

            # Only draw if 'drawing' is True
            if drawing:
                center = (x_index, y_index)

                if center:
                    if y_index <= 65:  # Button area
                        if 40 <= x_index <= 140:
                            if not canvas_cleared:  # Only clear if not already cleared
                                print("Clearing canvas...")
                                bpoints, gpoints, rpoints, ypoints = [deque(maxlen=1024) for _ in range(4)]
                                blue_index = green_index = red_index = yellow_index = 0
                                paintWindow[67:, :, :] = 255
                                canvas_cleared = True
                        elif 160 <= x_index <= 255:
                            colorIndex = 0
                            canvas_cleared = False
                        elif 275 <= x_index <= 370:
                            colorIndex = 1
                            canvas_cleared = False
                        elif 390 <= x_index <= 485:
                            colorIndex = 2
                            canvas_cleared = False
                        elif 505 <= x_index <= 600:
                            colorIndex = 3
                            canvas_cleared = False
                    else:
                        # Reset current color stroke if drawing stops
                        if colorIndex == 0:
                            if blue_index >= len(bpoints):
                                bpoints.append(deque(maxlen=1024))
                            bpoints[blue_index].append(center)
                        elif colorIndex == 1:
                            if green_index >= len(gpoints):
                                gpoints.append(deque(maxlen=1024))
                            gpoints[green_index].append(center)
                        elif colorIndex == 2:
                            if red_index >= len(rpoints):
                                rpoints.append(deque(maxlen=1024))
                            rpoints[red_index].append(center)
                        elif colorIndex == 3:
                            if yellow_index >= len(ypoints):
                                ypoints.append(deque(maxlen=1024))
                            ypoints[yellow_index].append(center)
    else:
        # Reset drawing when no hand is detected
        drawing = False

    # Draw all strokes
    points = [bpoints, gpoints, rpoints, ypoints]
    for i in range(4):
        for j in range(len(points[i])):
            for k in range(1, len(points[i][j])):
                if points[i][j][k - 1] is None or points[i][j][k] is None:
                    continue
                cv2.line(frame, points[i][j][k - 1], points[i][j][k], colors[i], 2)
                cv2.line(paintWindow, points[i][j][k - 1], points[i][j][k], colors[i], 2)

    # Show windows
    cv2.imshow("AirWhiteboard - Camera View", frame)
    cv2.imshow("Paint Canvas", paintWindow)

    # Log "q" prompt every few seconds only
    if time.time() - last_log_time > 5:
        print("Waiting for 'q' to quit...")
        last_log_time = time.time()

    key = cv2.waitKey(1)
    if key != -1:
        key = key & 0xFF
        if key == ord("q"):
            print("👋 Exiting AirWhiteboard...")
            break

# Cleanup
cap.release()
cv2.destroyAllWindows()
