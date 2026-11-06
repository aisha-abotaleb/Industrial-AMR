import cv2
import numpy as np

cap = cv2.VideoCapture(0)

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

marker_size = 0.05 

fx, fy, cx, cy = 600, 600, 320, 240
camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float32)
dist_coeffs = np.zeros((5, 1))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, marker_size, camera_matrix, dist_coeffs)
        
        for i, marker_id in enumerate(ids):
            cv2.aruco.drawDetectedMarkers(frame, corners)
            
            x = tvecs[i][0][0]
            y = tvecs[i][0][1]
            z = tvecs[i][0][2]

            cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvecs[i], tvecs[i], 0.03)

            text = f"Tag ID:{marker_id[0]} X:{x:.2f} Y:{y:.2f} Z:{z:.2f}m"
            center = (int(corners[i][0][0][0]), int(corners[i][0][0][1]))
            cv2.putText(frame, text, (center[0] - 30, center[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow('AprilTag Live Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()