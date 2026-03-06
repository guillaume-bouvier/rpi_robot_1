from gpiozero import DistanceSensor
import time
import math
import threading

from engine import Servo
from pca9685 import PCA9685, SERVO_MOTOR_PWM5

DEFAULT_STEP = 2

class Mapper:
    def __init__(self, pwm, trigger_pin, echo_pin):
        self.pwm = pwm
        self.ultra_sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin)
        self.servo = Servo(SERVO_MOTOR_PWM5, self.pwm)
        self.polar_map = [0] * 181
        self.scanning = False
    
    def get_distance(self):
        return self.ultra_sensor.distance * 100  # Convert to centimeters

    def get_angle(self):
        return self.servo.angle

    def start_continuous_scan(self, step=DEFAULT_STEP):
        scan_thread = threading.Thread(target=self.continuous_scan, args=(step,))
        scan_thread.start()
    
    def stop_continuous_scan(self):
        self.scanning = False
    
    def continuous_scan(self, step=DEFAULT_STEP):
        self.scanning = True
        while self.scanning:
            for angle in [range(0, 181, step) + range(180, -1, -step)]:
                if not self.scanning:
                    break
                self.servo.set_angle(angle)
                time.sleep(0.5)  # Allow time for servo to move and sensor to stabilize
                distance = self.get_distance()
                self.polar_map[angle] = distance

    def scan_environment(self, step=DEFAULT_STEP):
        for angle in range(0, 181, step):
            self.servo.set_angle(angle)
            time.sleep(0.5)  # Allow time for servo to move and sensor to stabilize
            distance = self.get_distance()
            self.polar_map[angle] = distance

    def get_polar_coordinates(self):
        distance = self.get_distance()
        angle = self.get_angle()
        return (distance, angle)

    def get_cartesian_coordinates(self):
        cartesian_map = []
        for distance, angle in self.polar_map:
            x = distance * math.cos(math.radians(angle))
            y = distance * math.sin(math.radians(angle))
            cartesian_map.append((x, y))
        return cartesian_map
