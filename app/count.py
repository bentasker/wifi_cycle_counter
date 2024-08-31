#!/usr/bin/env python3
#
# Cycle computer using Raspberry Pi GPIO Pins
#
#


import RPi.GPIO as GPIO
import datetime
 
GPIO_NUM=4
 
def detected_change(channel):
    if GPIO.input(channel) == GPIO.HIGH:
        print('\n1  at ' + str(datetime.datetime.now()))
 
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_NUM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(GPIO_NUM, GPIO.BOTH, callback=detected_change)
 
    message = input('Press enter to exit')
 
finally:
    GPIO.cleanup()
