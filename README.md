diy-bookscanner
===============
This repo contains, at the moment, the [main script](bookscanner.py) and [LCD module](lcd.py) for running a [DIY bookscanner](http://www.diybookscanner.org/) using a [Raspberry Pi](http://www.raspberrypi.org/).  The script, bookscanner.py, is derived from Mark Van den Borre's [test_keypedal.sh](https://github.com/markvdb/diybookscanner/blob/master/misc/test_keypedal.sh).  Per correspondence with Mark, this code is released under the AGPL.  

Like test_keypedal.sh, this script uses [gphoto](http://www.gphoto.org/) and [libptp2](http://libptp.sourceforge.net/) to communicate with the cameras, in this case a pair of Canon A2200 point-and-shoots.  It also relies on the [Canon Hack Development Kit (CHDK)](http://chdk.wikia.com/), enhanced firmware for selected Canon cameras.

The user interface for this system consists of a [20x4 LCD screen](http://www.adafruit.com/products/198) for output and a [foot switch](http://www.adafruit.com/products/423) for input.  The Raspberry Pi talks to both devices using [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO).  The code in lcd.py is largely derived from that in [Matt Hawkins' article "20×4 LCD Module Control Using Python"](http://www.raspberrypi-spy.co.uk/2012/08/20x4-lcd-module-control-using-python/).

![Raspberry Pi enclosure with LCD](images/rpi-enclosure.jpg)

Other details
-------------
The triggering script, bookscanner.py, is part of a larger system, including

* an init script, so that bookscanner.py will run as a daemon on boot
* an arrangement of wireless adapter and hostapd, so that the device acts as an access point
* the Apache web server and a web page for displaying scanned images and instructions
* a [real-time clock](https://www.adafruit.com/products/264), to allow the Pi to keep time in the absence of a network connection

Because the Raspberry Pi only has two USB ports, this system uses a [powered USB hub](http://www.adafruit.com/products/961) to connect the cameras and wireless adapter.