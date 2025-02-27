#!/usr/bin/env python3
#
# Cycle computer using Raspberry Pi GPIO Pins
#
# When invoked, this script will run forever, periodically
# writing line protocol to stdout
#
# It's intended to be run as a Telegraf execd plugin

'''
Copyright 2024 B Tasker

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import os
import RPi.GPIO as GPIO
import sys
import time

from math import pi

# Which GPIO should be used 
GPIO_NUM = int(os.getenv("RPI_GPIO_NUM", 4))

# This is based on what the computer does. I could probably
# grumble for a while about how it doesn't take the level of effort
# at different resistances into account though
CYCLES_PER_CALORIE=int(os.getenv("CYCLES_PER_CALORIE", 7 ))
 
# How often should we check counts
POLL_INTERVAL=int(os.getenv("CYCLES_POLL_INTERVAL", 5 ))
POLL_DEBOUNCE_MS=int(os.getenv("POLL_DEBOUNCE_MS", 100 ))

# How often should we write out stats?
WRITE_INTERVAL=int(os.getenv("CYCLES_WRITE_INTERVAL", 30 ))
WRITE_NO_CHANGE= (os.getenv("CYCLES_WRITE_NOCHANGE", "true" ).lower()  == "true")

# Do we want to calculate distance and speed? 
# On an exercise bike it's a fairly meaningless number, but can be interesting
# purely as an indicator
CALCULATE_DISTANCE=(os.getenv("CALCULATE_DISTANCE", "true" ).lower()  == "true")
WHEEL_RADIUS=float(os.getenv("WHEEL_RADIUS_CM", "5.6" ))
SPEED_FORMAT=os.getenv("SPEED_FORMAT", "mph" ).lower()

# Line Protocol Config
INFLUXDB_MEASUREMENT = os.getenv("INFLUXDB_MEASUREMENT", "cycle_activity")
INFLUXDB_EXTRA_TAGS = os.getenv("INFLUXDB_EXTRA_TAGS", "")
PRECISION = int(os.getenv("FLOAT_PRECISION", 2))


def detected_change(channel):
    ''' A change to the GPIO pin was detected
    '''
    global COUNTER
    if GPIO.input(channel) == GPIO.HIGH:
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
    speeds = []
    for entry in buffer:
        stats['total_cycles'] += entry[1]
        
        if entry[1] > stats['max']:
            stats['max'] = entry[1]
            
        if entry[1] < stats['min']:
            stats['min'] = entry[1]
            
        if CALCULATE_DISTANCE:
            # Calculate the speed in cm/s
            speeds.append((WHEEL_CIRCUMFERENCE * entry[1]) / POLL_INTERVAL)
        
        
    # Are supposed to continue to write if there's nothing to report?
    if stats['total_cycles'] == 0 and not WRITE_NO_CHANGE:
        return
    
    # Otherwise calculate additional stats
    stats['mean'] = stats['total_cycles'] / len(buffer)
    stats['rate'] = stats['total_cycles'] / time_period
    stats['calories'] = stats['total_cycles'] / CYCLES_PER_CALORIE
    
    # Average RPM 
    # If I do 5 rotations in 20s, that should come out as 15/min
    normalised_time = time_period / 60
    # 0.33
    stats['rpm'] = stats['total_cycles'] / normalised_time
    # 5 / 0.33 = 15
    # Conversely, if we've collected 100 cycles across 5 mins 
    # rpm should be 20
    #
    # 300 / 60 = 5
    # 100 / 5 = 20
    
    # Calculate distance and speed if enabled
    if CALCULATE_DISTANCE:
        distance = WHEEL_CIRCUMFERENCE * stats['total_cycles']
        mean_speed = distance / time_period
        stats['distance_cm'] = distance
        stats['speed'] = convert_speed(mean_speed)
        stats['max_speed'] = convert_speed(max(speeds))
    
    # Pass off for formatting and output
    output_lp(stats)


def convert_speed(sp):
    ''' Convert a speed from cm/s to something else
    '''
    # Convert from cm/s
    if SPEED_FORMAT == "mph":
         return sp / 44.704
    elif SPEED_FORMAT == "kph":
        return sp * 0.036
    # I wouldn't suggest using these, the numbers may
    # make you feel *really* bad
    elif SPEED_FORMAT == "parsec_hour":
        return (sp / 3085677599999995400) * 3600
    elif SPEED_FORMAT == "badgers_hour":
        return (sp / 80) * 3600
    elif SPEED_FORMAT == "lightyear_hour":
        return (sp / 946073047258094000) * 3600
    else:
        return sp   
    
    
    
    
def output_lp(stats):
    ''' Build line protocol and write to stdout
    '''
    
    ts = str(time.time_ns())
    
    # Start building the LP
    # the tagset includes some elements on config
    # allowing them to be used in queries if desired
    lp_1 = [
        INFLUXDB_MEASUREMENT,
        f"poll_interval={POLL_INTERVAL}",
        f"cycles_per_cal={CYCLES_PER_CALORIE}",       
        ]

    if CALCULATE_DISTANCE:
        lp_1.append(f"wheel_radius={WHEEL_RADIUS}")
        lp_1.append(f"speed_format={SPEED_FORMAT}")
        
    if len(INFLUXDB_EXTRA_TAGS) > 0:
        lp_1.append(INFLUXDB_EXTRA_TAGS)
    
    fields = []
    for m in stats:
        if isinstance(stats[m], float):
            fields.append(f"{m}={round(stats[m], PRECISION)}")
        else:
            fields.append(f"{m}={stats[m]}i")
        
    # concatenate to build a line of line protocol
    lp_prefix = ",".join(lp_1)
    lp_suffix = ",".join(fields)
    lp = ' '.join([lp_prefix, lp_suffix, ts])
    
    # Print it
    print(lp)


if __name__ == "__main__":
    # Define the counters etc
    COUNTER = 0
    LAST_COUNTER = 0    
    
    if POLL_INTERVAL < 1:
        print(f"Poll interval must be at least 1 (current: {POLL_INTERVAL})", file=sys.stderr)
        sys.exit(1)

    # If we're supposed to be calculating distance, 
    # calculate the wheel circumference from the radius measurement
    if CALCULATE_DISTANCE:
        WHEEL_CIRCUMFERENCE = 2 * pi * WHEEL_RADIUS
        if SPEED_FORMAT not in ["mph", "kph", "parsec_hour", "badgers_hour", "lightyear_hour"]:
            print("Unsupported speed format provided, using cm/s", file=sys.stderr)
            SPEED_FORMAT = "cm/s"

    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_NUM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(
        GPIO_NUM, 
        GPIO.RISING, 
        callback=detected_change,
        bouncetime=POLL_DEBOUNCE_MS
        )

    stats_buffer = []

    # Start iterating
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
