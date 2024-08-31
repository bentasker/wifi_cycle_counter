#!/usr/bin/env python3
#
# Cycle computer using Raspberry Pi GPIO Pins
#
#


import datetime
import os
import RPi.GPIO as GPIO
import sys
import time
 
GPIO_NUM = int(os.getenv("RPI_GPIO_NUM", 4))

# This is based on what the computer does. I could probably
# grumble for a while about how it doesn't take the level of effort
# at different resistances into account though
CYCLES_PER_CALORIE=int(os.getenv("CYCLES_PER_CALORIE", 7 ))
 
# How often should we check counts
POLL_INTERVAL=int(os.getenv("CYCLES_POLL_INTERVAL", 5 ))

 
def detected_change(channel):
    ''' A change to the GPIO pin was detected
    '''
    global COUNTER
    if GPIO.input(channel) == GPIO.HIGH:
        print('\n1  at ' + str(datetime.datetime.now()))
        COUNTER += 1


# Define the counter
COUNTER = 0
LAST_COUNTER = 0

if POLL_INTERVAL < 1:
    print("Poll interval must be at least 1")
    sys.exit(1)

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_NUM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(GPIO_NUM, GPIO.RISING, callback=detected_change)
 
while True:
    time.sleep(POLL_INTERVAL)
    difference = COUNTER - LAST_COUNTER
    LAST_COUNTER = COUNTER
    
    # What's the average rate of rotation?
    rate = difference / POLL_INTERVAL

    # TODO: calorie calculation
    #
    # This one's a bit harder - do we calculate fractions
    # or do we just carry any difference over?
    
    print(f"{difference} cycles (avg {rate}/s)")
    

GPIO.cleanup()
