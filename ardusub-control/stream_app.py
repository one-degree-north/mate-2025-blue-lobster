import sys
import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from pylint import mavutil

class VideoStreamApp(QMainWindow):
    def __init__(self, udp_url: str):
        super().__init__()
        self.setWindowTitle("UDP Video Stream and Thruster Control")
        self.setGeometry(100, 100, 800, 600)

        # Video display widget
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.video_label)

        # Timer to fetch frames
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # OpenCV VideoCapture
        self.cap = cv2.VideoCapture(udp_url)

        # Start streaming if the video source is valid
        if self.cap.isOpened():
            self.timer.start(30)  # Adjust to ~30 FPS
        else:
            self.video_label.setText("Failed to open video stream.")
            self.cap.release()

        # MAVLink connection setup (updated with the new IP address)
        self.master = mavutil.mavlink_connection('udp:192.168.2.1:14550')  # Updated connection string
        self.master.wait_heartbeat()  # Wait for the heartbeat to confirm the connection
        print("Heartbeat received. Connected to vehicle.")

        # Arm the vehicle for control
        self.arm_vehicle()

    def arm_vehicle(self):
        """Arms the vehicle for control."""
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        print("Vehicle armed.")

    def set_rc_channel_pwm(self, channel_id, pwm_value):
        """Sets PWM value to control thrusters."""
        if channel_id < 1 or channel_id > 18:
            print("Invalid channel ID.")
            return

        # List of 18 RC channels, defaulting to "no change"
        rc_channel_values = [65535] * 18
        rc_channel_values[channel_id - 1] = pwm_value

        # Send RC override command
        self.master.mav.rc_channels_override_send(
            self.master.target_system,
            self.master.target_component,
            *rc_channel_values
        )

    def update_frame(self):
        """Fetch and display a new frame."""
        ret, frame = self.cap.read()
        if ret:
            # Convert frame to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Create a QImage from the frame
            h, w, ch = frame.shape
            q_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            # Display the QImage as a QPixmap
            self.video_label.setPixmap(QPixmap.fromImage(q_img))
        else:
            self.video_label.setText("Failed to fetch frame.")

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_W:
            print("Moving forward...")
            self.set_rc_channel_pwm(2, 1700)  # Channel 3 for forward movement (adjust as per your setup)
        elif event.key() == Qt.Key.Key_S:
            print("Stopping...")
            self.set_rc_channel_pwm(2, 1500)  # Neutral PWM to stop
        elif event.key() == Qt.Key.Key_Q:
            print("Quitting...")
            self.close()

    def closeEvent(self, event):
        """Release resources on close."""
        self.timer.stop()
        self.cap.release()
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0, 0, 0, 0, 0, 0, 0
        )  # Disarm the vehicle on exit
        print("Vehicle disarmed.")
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    udp_url = "http://blueos.local/mavlink-camera-manager/sdp?source=%2Fdev%2Fvideo6"  # Replace with your video stream URL
    window = VideoStreamApp(udp_url)
    window.show()
    sys.exit(app.exec())
