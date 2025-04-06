import cv2

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

if ret:
    cv2.imwrite("test_frame.jpg", frame)
    print("Captured successfully!")
else:
    print("Failed to capture")