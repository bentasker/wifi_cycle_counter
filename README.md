# Raspberry Pi Cycle Computer

This is a simple script to use a Raspberry Pi's GPIO pins in conjunction with a reed switch to create a simple cycle computer, which will write stats out to an [InfluxDB](https://github.com/influxdata/influxdb) instance.

It was created with an exercise bike in mind: I have an under-desk setup and it was bugging me that I couldn't see how much use I actually make of it, so I decided to [build a replacement cycle computer](https://www.bentasker.co.uk/posts/blog/house-stuff/building-a-smart-wifi-cycle-computer-with-rpi-influxdb-and-grafana.html)

---

### Pre-Requisites

It's assumed that you already have

* A Raspberry Pi (I prototyped on a 3 and then then used a Zero 2W)
* Installed an OS and configured connectivity on your Pi ([examples](https://raspberrytips.com/raspberry-pi-wifi-setup/))
* Installed the [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) library

---

### Setup Instructions

Install Telegraf 
```sh 
curl --silent --location -O \
https://repos.influxdata.com/influxdata-archive.key \
&& echo "943666881a1b8d9b849b74caebf02d3465d6beb716510d86a39f6c8e8dac7515  influxdata-archive.key" \
| sha256sum -c - && cat influxdata-archive.key \
| gpg --dearmor \
| sudo tee /etc/apt/trusted.gpg.d/influxdata-archive.gpg > /dev/null \
&& echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive.gpg] https://repos.influxdata.com/debian stable main' \
| sudo tee /etc/apt/sources.list.d/influxdata.list
sudo apt-get update && sudo apt-get install telegraf
```

Add the `telegraf` user to the `gpio` group
```sh
adduser telegraf gpio
```

Clone this repo down
```sh
git clone https://github.com/bentasker/wifi_cycle_counter.git
sudo mv wifi_cycle_counter /usr/local/src/
```

---

### Config

The easiest way to get started is to copy `config/telegraf.conf.example` to `/etc/telegraf/telegraf.conf` and then edit it
```sh 
sudo cp config/telegraf.conf.example /etc/telegraf/telegraf.con
sudo nano /etc/telegraf/telegraf.con
```

You will need to

* Update the plugin config section to provide the path to `count.py` (if you installed in a different location)
* Update the output section with details of your InfluxDB instance

---

### Starting

Once you're ready, you should just need to restart Telegraf (note: not reload - we need Telegraf to pick up the new group)

```sh
systemctl restart telegraf
```

---

### Config Vars

The script has a range of configuration vars, each of which can be set in the `environment` section in Telegraf's config 

* `GPIO_NUM`: which GPIO should we bind to (default is 4: pin 7)
* `CYCLES_PER_CALORIE`: how many rotations per calorie (default 7)
* `POLL_INTERVAL`: How often should the script calculate how many rotations have happened? (default 5)
* `WRITE_INTERVAL`: How often should the script write out a set of stats (should be >= `POLL_INTERVAL`, default 30)
* `WRITE_NO_CHANGE`: Should we write a point even if there have been no rotations (default true)
* `CALCULATE_DISTANCE`: Should we calculate distance and speed?
* `WHEEL_RADIUS`: What wheel radius (in cm) should we use to calculate distance/speed (default 5.6)
* `SPEED_FORMAT`: What unit should we use for speed (`mph`, `kph`, `cm/s`. Default `mph`)
* `INFLUXDB_MEASUREMENT`: InfluxDB measurement to use in generate line protocol (default: "cycle_activity")
* `INFLUXDB_EXTRA_TAGS`: Additional tags to inject into line protocol (default: "". Example "foo=bar,sed=zoo")
* `PRECISION`: Number of decimal places to include in floats

---

### Copyright

Copyright (c) 2024 B Tasker
Released under [BSD 3-Clause License](https://opensource.org/license/BSD-3-Clause)
