from .pca9685 import (
    SERVO_MOTOR_PWM3,
    SERVO_MOTOR_PWM4,
    DC_MOTOR_PWM1,
    DC_MOTOR_INA1,
    DC_MOTOR_INA2,
    DC_MOTOR_PWM2,
    DC_MOTOR_INB1,
    DC_MOTOR_INB2
)

import time
import threading

# Init min and max angles
SERVO_MIN = 520
SERVO_MAX = 2500

# TTMotor Default Speed
TTMOTOR_DEFAULT_SPEED = 19000


class Engine:
    def __init__(self, pwm):
        self.pwm = pwm
        self.pwm.setPWMFreq(50)

        self.servos = {
            'x': Servo(SERVO_MOTOR_PWM4, self.pwm),
            'y': Servo(SERVO_MOTOR_PWM3, self.pwm),
        }
        
        self.motors = {
            'left': TTMotor(self.pwm, DC_MOTOR_PWM1, DC_MOTOR_INA1, DC_MOTOR_INA2),
            'right': TTMotor(self.pwm, DC_MOTOR_PWM2, DC_MOTOR_INB1, DC_MOTOR_INB2),
        }


    def set_motor_status(self, motor_status, speed=TTMOTOR_DEFAULT_SPEED):
        for motor_id, motor_direction  in enumerate(motor_status):
            self.motors[motor_id].fn_motor_direction[motor_direction](speed)


class TTMotor:
    def __init__(self, pwm, pwm_channel, in1, in2):
        self.pwm = pwm
        self.pwm_channel = pwm_channel
        self.in1 = in1
        self.in2 = in2

        self.fn_motor_direction = {
            -1: self.set_motor_backward,
            0: self.set_motor_stop,
            1: self.set_motor_forward,
        }

    def set_motor_forward(self, speed):
        self.pwm.setServoPulse(self.pwm_channel, 15000)
        self.pwm.setServoPulse(self.in1, 0)
        self.pwm.setServoPulse(self.in2, speed)
    
    def set_motor_backward(self, speed):
        self.pwm.setServoPulse(self.pwm_channel, 15000)
        self.pwm.setServoPulse(self.in1, speed)
        self.pwm.setServoPulse(self.in2, 0)
    
    def set_motor_stop(self):
        self.pwm.setServoPulse(self.pwm_channel, 0)


class Servo:
    def __init__(self, address, pwm, start_angle=90):
        self.address = address
        self.angle_map = [0] * 181
        self.angle = None
        self.min_angle = SERVO_MIN
        self.max_angle = SERVO_MAX
        self.pwm = pwm
        self.move = True
        self.step = 1
        self.sleep = 0.01
        self.thread = None

        self._init_angles()
        self.set_angle(start_angle)
    
    def set_angle(self, angle):
        # Ignores the self.moving variable
        self.pwm.setServoPulse(self.address, self.angle_map[angle])
        self.angle = angle

    def move_towards(self, target_angle):
        self.move = True
        self.thread = threading.Thread(
            target=self._move_to_angle_by_steps,
            args=(target_angle,),
        )
        self.thread.start()

    def stop_moving(self):
        self.move = False
        self.thread.join()

    def set_servo_off(self):
        self.pwm.setServoPulse(self.address, 0)
    
    def _init_angles(self):
        angle_step = (self.max_angle - self.min_angle) / 180
        for i in range(0, 181):
            self.angle_map[i] = self.min_angle + (i*angle_step)

    def _move_to_angle_by_steps(self, target_angle):
        while self.move and self.angle != target_angle:
            if self.angle < target_angle:
                increment = min(self.step, target_angle - self.angle)
            if self.angle > target_angle:
                increment = -min(self.step, self.angle - target_angle)

            next_angle = self.angle + increment

            self.set_angle(next_angle)
            time.sleep(self.sleep)
