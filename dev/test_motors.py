from library import motor_control
import time

motor = motor_control.Engine()

def test_class():
    print(motor_control.ANGLES)


def test_servo(servo_id):
    for angle in (0, 45, 90, 135, 180, 90):
        motor.set_servo_angle(servo_id, angle)
        time.sleep(1)

    motor.set_servo_off(servo_id)


def test_movements():
    directions = [
        (1, 1),
        (-1, -1),
        (0, 0),
        (1, -1),
        (-1, 1),
        (1, 0),
        (0, 1),
        (-1, 0),
        (0, -1),
        (0, 0),
    ]

    for direction in directions:
        motor.set_motor_status(direction)
        time.sleep(0.5)


if __name__ == '__main__':
    test_class()
    test_servo(0)
    test_servo(1)
    # test_movements()