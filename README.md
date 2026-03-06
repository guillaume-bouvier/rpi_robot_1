# rpi_robot_1

## APIs

### Info
- GET /api/service/battery
- GET /api/service/cpu_temp

### Servo
- GET /api/servo/id
- POST /api/servo/id/config
- POST /api/servo

### Motor
- POST /api/motor

### Key
- POST /api/key
- DELETE /api/key

### Video
- GET /video

### Web socket
- connect: increment the # of clients
- disconnect: if no client left, stop camera