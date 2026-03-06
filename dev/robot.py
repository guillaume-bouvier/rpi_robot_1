# import library.pca9685 as pca9685
from flask import Flask, request, jsonify, Response, send_file
from flask_socketio import SocketIO
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
from libcamera import controls
import io

import threading
from threading import Condition
import time 

from library.motor_control import Engine

motor = Engine()

app = Flask(__name__)
socketio = SocketIO(app)
# CORS(app, resources={r"/command": {"origins": "*"}})  # Customize as needed

# To manage the streaming state
clients = 0
streaming = False
lock = threading.Lock()

# Initialize the camera
camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
encoder = JpegEncoder()
camera.start_encoder(encoder)

motor_states = [0, 0]
commands = {
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


def update_motor_states(command):
    global motor_states
    motor_states = commands.get(command, motor_states)
    print(f"Updated motor states: {motor_states}")

    motor.set_motor_status(motor_states)

    return motor_states


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


# def generate_frames():
#     while True:
#         with lock:
#             if clients == 0 and not streaming:
#                 break
#         # Capture frame-by-frame
#         frame = picam2.capture_array()
        
#         # Convert the frame to JPEG
#         ret, buffer = cv2.imencode('.jpg', frame)
#         frame = buffer.tobytes()
        
#         # Yield the output frame in byte format
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


#defines the function that generates our frames
def generate_frames():
    output3 = StreamingOutput()
    output2 = FileOutput(output3)
    encoder.output = [output2]

    camera.set_controls({"AfMode":controls.AfModeEnum.Continuous})
    time.sleep(20) 
    print('done')
    while True:
        with lock:
            if clients == 0 and not streaming:
                break

        with output3.condition:
            output3.condition.wait()
        frame = output3.frame
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


#defines the route that will access the video feed and call the feed function
@app.route('/cam')
def video_feed():
    global streaming
    with lock:
        if not streaming:
            camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
            camera.start()
            camera.set_controls({"AfMode":controls.AfModeEnum.Continuous})
            streaming = True
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    command = data.get('command')
    updated_states = update_motor_states(command)
    if command:
        return jsonify({'status': 'success', 'motor_states': updated_states})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid command'}), 400


@socketio.on('connect')
def handle_connect():
    global clients
    with lock:
        clients += 1


@socketio.on('disconnect')
def handle_disconnect():
    global clients, streaming
    with lock:
        clients -= 1
        if clients == 0:
            camera.stop()
            streaming = False

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
