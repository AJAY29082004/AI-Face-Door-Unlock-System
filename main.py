import cv2
import os
import numpy as np
import requests
import time
from sklearn.neighbors import KNeighborsClassifier

# ================= CONFIG =================
IMG_SIZE = 100
DATASET_DIR = "dataset"
ESP_IP = "192.168.4.1"
ESP_URL = f"http://{ESP_IP}/unlock"

UNLOCK_COOLDOWN = 10      # seconds
UNLOCK_DISPLAY_TIME = 5  # seconds

os.makedirs(DATASET_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

door_status = "LOCKED"
last_unlock_time = 0

# ================= DATA COLLECTION =================
def collect_faces():
    cap = cv2.VideoCapture(0)
    name = input("Enter person name: ")

    person_dir = os.path.join(DATASET_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    print("Press [c]=capture | [t]=train | [q]=quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.imshow("Collect Faces", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c') and len(faces) > 0:
            x, y, w, h = faces[0]
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (IMG_SIZE, IMG_SIZE))
            count = len(os.listdir(person_dir))
            cv2.imwrite(f"{person_dir}/{count}.jpg", face)
            print("Saved image", count)

        elif key == ord('t'):
            break

        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    cap.release()
    cv2.destroyAllWindows()

# ================= TRAIN MODEL =================
def train_model():
    X, y, label_map = [], [], {}
    label_id = 0

    for person in os.listdir(DATASET_DIR):
        person_path = os.path.join(DATASET_DIR, person)
        if not os.path.isdir(person_path):
            continue

        label_map[label_id] = person

        for img in os.listdir(person_path):
            img_path = os.path.join(person_path, img)
            face = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            face = cv2.resize(face, (IMG_SIZE, IMG_SIZE))
            X.append(face.flatten())
            y.append(label_id)

        label_id += 1

    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(np.array(X), np.array(y))
    print("Training completed")
    return model, label_map

# ================= LIVE RECOGNITION =================
def live_recognition(model, label_map):
    global door_status, last_unlock_time

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (IMG_SIZE, IMG_SIZE))
            face_flat = face.flatten().reshape(1, -1)

            pred = model.predict(face_flat)[0]
            name = label_map[pred]

            current_time = time.time()

            # ===== UNLOCK ONLY ON COOLDOWN =====
            if current_time - last_unlock_time > UNLOCK_COOLDOWN:
                try:
                    requests.get(ESP_URL, timeout=1)
                    last_unlock_time = current_time
                    door_status = "UNLOCKED"
                    print("Door unlocked")
                except requests.exceptions.RequestException:
                    print("ESP not reachable")

            cv2.putText(frame, name, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # ===== AUTO LOCK DISPLAY =====
        if time.time() - last_unlock_time > UNLOCK_DISPLAY_TIME:
            door_status = "LOCKED"

        cv2.putText(frame, f"DOOR: {door_status}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                    (0, 255, 0) if door_status == "UNLOCKED" else (0, 0, 255), 3)

        cv2.imshow("Face Door Unlock System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ================= RUN =================
collect_faces()
model, labels = train_model()
live_recognition(model, labels)
