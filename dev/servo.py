from library.pca9685 import PCA9685, SERVO_MOTOR_PWM3, SERVO_MOTOR_PWM4
import time

pwm = PCA9685()
pwm.setPWMFreq(50) # for servo

"""The following code is applied to servo motor control"""
for i in range(520,2500,10):# start 500, end 2500, step is 10  
    print(i)
    pwm.setServoPulse(SERVO_MOTOR_PWM4,i)   
    time.sleep(0.01)    
print("servo cw")
for i in range(2500,520,-10):
    print(i)
    pwm.setServoPulse(SERVO_MOTOR_PWM4,i) 
    time.sleep(0.01)  