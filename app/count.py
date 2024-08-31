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

# How often should we write out stats?
WRITE_INTERVAL=int(os.getenv("CYCLES_WRITE_INTERVAL", 30 ))
WRITE_NO_CHANGE= (os.getenv("CYCLES_WRITE_NOCHANGE", "true" ).lower()  == "true")

 
def detected_change(channel):
    ''' A change to the GPIO pin was detected
    '''
    global COUNTER
    if GPIO.input(channel) == GPIO.HIGH:
        #print('\n1  at ' + str(datetime.datetime.now()))
        COUNTER += 1

def aggregate_and_write(buffer):
    ''' Take a stats buffer and generate a datapoint from it
    '''
    
    first_time = buffer[0][0]
    end_time = buffer[-1][0]
    time_period = end_time - first_time
    
    total_cycles = 0
    for entry in buffer:
        total_cycles += entry[1]
    
    rate = total_cycles / time_period
    calories = total_cycles / CYCLES_PER_CALORIE
    
    print(f"{total_cycles} cycles (avg {rate}/s, {calories}cal) measured over {time_period}s")


# Define the counter
COUNTER = 0
LAST_COUNTER = 0

if POLL_INTERVAL < 1:
    print("Poll interval must be at least 1")
    sys.exit(1)

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_NUM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(GPIO_NUM, GPIO.RISING, callback=detected_change)

stats_buffer = []
last_write = time.time()
while True:
    difference = COUNTER - LAST_COUNTER
    LAST_COUNTER = COUNTER
    now = time.time()
    
    stats_buffer.append([
        now,
        difference
        ])

    # Have we reached a write interval?
    if (now - last_write) > WRITE_INTERVAL:
        aggregate_and_write(stats_buffer)
        stats_buffer = []
        last_write = now

    time.sleep(POLL_INTERVAL)

GPIO.cleanup()
