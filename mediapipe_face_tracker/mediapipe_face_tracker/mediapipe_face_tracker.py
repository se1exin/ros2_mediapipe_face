import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point

# Media pip libs
import cv2
import mediapipe as mp
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

BUFFER_SIZE = 3
MIN_CONFIDENCE = 0.75

class MediapipeFaceTracker(Node):
    def __init__(self, cap):
        super().__init__("mediapipe_face_tracker")
        self.cap = cap

        self.location_publisher = self.create_publisher(Point, "/mediapipe_face_tracker/location", 10)

        self.x_buffer = []
        self.y_buffer = []
        self.z_buffer = []

        self.track_faces()

    def track_faces(self):
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            while self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    self.get_logger().info("Ignoring empty camera frame.")
                    continue
                
                # Flip the image horizontally for a selfie-view display.
                image = cv2.flip(image, 1)
                
                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = face_detection.process(image)

                # Draw the face detection annotations on the image.
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                if results.detections:
                    for detection in results.detections:
                        if detection.score[0] < MIN_CONFIDENCE:
                            continue
                        self.handle_detection(detection)
                        mp_drawing.draw_detection(image, detection)
                
                cv2.namedWindow('img', cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                cv2.imshow('img', image)
                if cv2.waitKey(5) & 0xFF == 27:
                    break

    def handle_detection(self, detection):
        loc_data = detection.location_data.relative_bounding_box
        point = Point()

        # Find the midpoint
        point_x = loc_data.xmin + (loc_data.width / 2)
        point_y = loc_data.ymin + (loc_data.height / 2)
        point_z = loc_data.width  # Use the width of the box as distance from screen

        if len(self.x_buffer) >= BUFFER_SIZE:
            self.x_buffer.pop(0)
        self.x_buffer.append(point_x)

        if len(self.y_buffer) >= BUFFER_SIZE:
            self.y_buffer.pop(0)
        self.y_buffer.append(point_y)

        if len(self.z_buffer) >= BUFFER_SIZE:
            self.z_buffer.pop(0)
        self.z_buffer.append(point_z)

        point.x = self.buffer_avg(self.x_buffer)
        point.y = self.buffer_avg(self.y_buffer)
        point.z = self.buffer_avg(self.z_buffer)
        self.location_publisher.publish(point)

    def buffer_avg(self, buffer):
        total = 0
        for val in buffer:
            total += val
        
        return total / len(buffer)

def main():
    rclpy.init()
    cap = cv2.VideoCapture(-1)
    node = MediapipeFaceTracker(cap)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    cap.release()
    rclpy.shutdown()
    

if __name__ == '__main__':
    main()
