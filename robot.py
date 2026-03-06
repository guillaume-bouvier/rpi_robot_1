# TODOs
# TODO: Change most of the endpoints to have a more standard implementation
# TODO: Implement web interface as CSR served from here
# TODO: Remove CORS if served from here
# TODO: Implement authorization
# TODO: Implement configuration change for camera


# Custom libraries
from library.engine import Engine
from library.pca9685 import PCA9685
from library.mapping import Mapper

# Web server imports
from flask import Flask, Response, send_file, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

# Camera Imports
from picamera2 import Picamera2
from libcamera import controls
import cv2

# Others
from datetime import datetime
import threading

# Constants
TRIGGER_PIN = 23
ECHO_PIN = 24

# Init Web app
print("Initializing web app...")
app = Flask(__name__)
CORS(app, resource={r"/*": {"origin": "*"}})
socketio = SocketIO(app)

# Init Camera
print("Starting PiCamera module...")
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.set_controls({"AfMode":controls.AfModeEnum.Continuous})

# To manage the streaming state
clients = 0
streaming = False
lock = threading.Lock()

# Init PCA9685
print("Initializing I2C PWM PCA9685...")
pwm = PCA9685()

# Init Motor information
print("Starting Engine...")
engine = Engine(pwm)
motor_states = [0, 0]
servo_states = [0, 0]

# Init Mapper
print("Initializing Mapper...")
mapper = Mapper(pwm, trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN)

motor_commands_to_state = {
    'up': [1, 1],
    'down': [-1, -1],
    'left': [-1, 1],
    'right': [1, -1],
    'upleft': [0, 1],
    'upright': [1, 0],
    'downleft': [-1, 0],
    'downright': [0, -1],
    'stop': [0, 0],
}

servo_commands_to_state = {
    'up': [1, 0],
    'down': [-1, 0],
    'left': [0, 1],
    'right': [0, -1],
    'upleft': [1, 1],
    'upright': [1, -1],
    'downleft': [-1, 1],
    'downright': [-1, -1],
    'stop': [0, 0],
}

servo_keys = {
    'ArrowUp': False,
    'ArrowLeft': False,
    'ArrowDown': False,
    'ArrowRight': False,
}

motor_keys = {
    'w': False,
    'a': False,
    's': False,
    'd': False,
}

key_to_command_map = {
    # w a s d
    (False, False, False, False) : 'stop',
    (False, False, False, True) : 'right',
    (False, False, True, False) : 'down',
    (False, False, True, True) : 'downright',
    (False, True, False, False) : 'left',
    (False, True, True, False) : 'downleft',
    (True, False, False, False) : 'up',
    (True, False, False, True) : 'upright',
    (True, True, False, False) : 'upleft', 
}


def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
            temp = file.read()
            # Convert the temperature to Celsius
            temp_celsius = float(temp) / 1000.0
            return temp_celsius
    except FileNotFoundError:
        return "Could not read CPU temperature. Make sure you are running this on a Raspberry Pi."


def update_motor_states():
    # global motor_states
    # motor_states = motor_commands.get(command, motor_states)
    # print(f"Updated motor states: {motor_states}")

    # # motor.set_motor_status(motor_states)
    key_state = (
        motor_keys['w'],
        motor_keys['a'],
        motor_keys['s'],
        motor_keys['d'],
    )

    if key_state in key_to_command_map:
        motor_states = key_to_command_map[key_state] 

    return motor_states


def update_servo_states(command):
    global servo_states
    servo_states = servo_commands_to_state.get(command, servo_states)

    return servo_states


def generate_frame():
    while True:
        frame = picam2.capture_array()
        # Convert the frame to a format that can be processed
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # frame = add_text_overlay(frame)
        # frame = add_cpu_temperature(frame)

        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')


def add_cpu_temperature(frame):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 255, 255)
    thickness = 2
    line_type = cv2.LINE_AA

    text = f"Cpu temp: {get_cpu_temperature()}C"
    position = (10, 40)
    cv2.putText(frame, text, position, font, font_scale, font_color, thickness, line_type)

    return frame


def add_text_overlay(frame):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 255, 255)
    thickness = 2
    line_type = cv2.LINE_AA

    text = "Live"
    position = (10, 40)
    cv2.putText(frame, text, position, font, font_scale, font_color, thickness, line_type)

    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    position = (10, 470)
    cv2.putText(frame, text, position, font, font_scale, font_color, thickness, line_type)
    
    return frame


# TODO: Finish implementation
@app.route('/rpi_batt', methods=['GET', 'OPTIONS'])
def rpi_batt():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'This is an OPTIONS response'})
        response.headers['Allow'] = 'OPTIONS, GET'
        return response
    else:
        return jsonify({'value': '?'})


@app.route('/cpu_temp', methods=['GET', 'OPTIONS'])
def cpu_temp():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'This is an OPTIONS response'})
        response.headers['Allow'] = 'OPTIONS, GET'
        return response
    else:
        return jsonify({'value': get_cpu_temperature()})


# TODO: Change this to GET with /servo/<x or y>
# Request Data
# { 'servo': <x or y> }
@app.route('/get_servo_info', methods=['POST', 'OPTIONS'])
def get_servo_info():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'This is an OPTIONS response'})
        response.headers['Allow'] = 'OPTIONS, POST'
        return response
    else:
        data = request.get_json()
        servo = data.get('servo')
        info = {
            'servo_min': engine.servos[servo].min_angle,
            'servo_max': engine.servos[servo].max_angle,
            'angle': engine.servos[servo].angle,
        }
        return jsonify(info)


# Request Data
# { 'servo': <x or y>, 'key': <config key to set>, 'value': <value> }
@app.route('/set_servo_config', methods=['POST', 'OPTIONS'])
def set_servo_info():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'This is an OPTIONS response'})
        response.headers['Allow'] = 'OPTIONS, POST'
        return response
    else:
        data = request.get_json()
        servo = data.get('servo')
        config_key = data.get('key')
        config_value = data.get('value')
        if config_key == 'min_angle':
            engine.servos[servo].min_angle = config_value
        elif config_key == 'max_angle':
            engine.servos[servo].max_angle = config_value
        else:
            return jsonify({'status': 'error', 'message': 'Invalid config'}), 400


@app.route('/motor', methods=['POST', 'OPTIONS'])
def motor_command():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'This is an OPTIONS response'})
        response.headers['Allow'] = 'OPTIONS, POST'
        return response
    else:
        data = request.get_json()
        command = data.get('command')
        if command:
            updated_states = update_motor_states(command)
            return jsonify({'status': 'success', 'motor_states': updated_states})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid command'}), 400


@app.route('/servo', methods=['POST'])
def servo_command():
    data = request.get_json()
    command = data.get('command')
    if command:
        updated_states = update_servo_states(command)
        return jsonify({'status': 'success', 'motor_states': updated_states})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid command'}), 400


@app.route('/key', methods=['POST'])
def add_command():
    data = request.get_json()
    key = data.get('key')
    if key in servo_keys:
        print(f'Received arrow key : {key}')
        servo_keys[key] = True
        update_servo_states(key_to_command_map[tuple(servo_keys.values())])
        return jsonify({'status': 'success', 'servo_states': servo_states})
    elif key in motor_keys:
        print(f'Received Motor key : {key}')
        return jsonify({'status': 'success', 'motor_states': servo_states})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid key'}), 400


@app.route('/key', methods=['DELETE'])
def remove_command():
    data = request.get_json()
    key = data.get('key')
    if key in servo_keys:
        print(f'Received delete arrow key : {key}')
        servo_keys[key] = False
        update_servo_states(key_to_command_map[tuple(servo_keys.values())])
        return jsonify({'status': 'success', 'servo_states': servo_states})
    elif key in motor_keys:
        print(f'Received deleteMotor key : {key}')
        return jsonify({'status': 'success', 'motor_states': servo_states})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid key'}), 400


@app.route('/video_feed')
def video_feed():
    global streaming
    with lock:
        if not streaming:
            picam2.start()
            streaming = True

    return Response(generate_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# TODO: Define if still required
@app.route('/')
def index():
    return send_file('index.html')


@socketio.on('connect')
def handle_connect():
    global clients
    with lock:
        clients += 1
        print(f"clients: {clients}")


@socketio.on('disconnect')
def handle_disconnect():
    global clients, streaming
    with lock:
        clients -= 1
        print(f"clients: {clients}")
        if clients == 0:
            picam2.stop()
            streaming = False


if __name__ == '__main__':
    print("Starting Web Application...")
    app.run(host='0.0.0.0', port=5000)
