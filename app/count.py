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
    stats = {}
    
    first_time = buffer[0][0]
    end_time = buffer[-1][0]
    time_period = end_time - first_time
    
    stats['total_cycles'] = 0
    stats['max'] = 0
    stats['min'] = 999999
    for entry in buffer:
        stats['total_cycles'] += entry[1]
        
        if entry[1] > stats['max']:
            stats['max'] = entry[1]
            
        if entry[1] < stats['min']:
            stats['min'] = entry[1]
        
    # Are supposed to continue to write if there's nothing to report?
    if stats['total_cycles'] == 0 and not WRITE_NO_CHANGE:
        return
    
    # Otherwise calculate additional stats
    
    # Average cycles per poll period
    stats['mean'] = stats['total_cycles'] / len(buffer)
    
    stats['rate'] = stats['total_cycles'] / time_period
    stats['calories'] = stats['total_cycles'] / CYCLES_PER_CALORIE
    write_to_influx(stats)
    

def write_to_influx(stats):
    ''' Build line protocol and write out
    '''
    print(stats)
    


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
while True:
    difference = COUNTER - LAST_COUNTER
    LAST_COUNTER = COUNTER
    now = time.time()
    
    stats_buffer.append([
        now,
        difference
        ])

    time.sleep(POLL_INTERVAL)
    
    # Have we reached a write interval? compare times
    if (stats_buffer[-1][0] - stats_buffer[0][0]) > WRITE_INTERVAL:
        aggregate_and_write(stats_buffer)
        stats_buffer = []


GPIO.cleanup()
