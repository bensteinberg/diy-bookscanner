diy-bookscanner
===============
This repo contains, at the moment, the [main script](bookscanner.py) and some additional code for running a [DIY bookscanner](http://www.diybookscanner.org/) using a [Raspberry Pi](http://www.raspberrypi.org/).  The script, bookscanner.py, is derived from Mark Van den Borre's [test_keypedal.sh](https://github.com/markvdb/diybookscanner/blob/master/misc/test_keypedal.sh).  Per correspondence with Mark, this code is released under the Affero GPL.  

Like test_keypedal.sh, this script uses [gphoto](http://www.gphoto.org/) and [libptp2](http://libptp.sourceforge.net/) to communicate with the cameras, in this case a pair of Canon A2200 point-and-shoots.  It also relies on the [Canon Hack Development Kit (CHDK)](http://chdk.wikia.com/), enhanced firmware for selected Canon cameras.

The user interface for this system consists of a [20x4 LCD screen](http://www.adafruit.com/products/198) for output and a [foot switch](http://www.adafruit.com/products/423) for input.  The Raspberry Pi talks to both devices using [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO).  The code in [lcd.py](lcd.py) is largely derived from that in [Matt Hawkins' article "20×4 LCD Module Control Using Python"](http://www.raspberrypi-spy.co.uk/2012/08/20x4-lcd-module-control-using-python/).

![Raspberry Pi enclosure with LCD](images/rpi-enclosure.jpg)

Other details
-------------
The triggering script, bookscanner.py, is part of a larger system, including

* an init script, so that bookscanner.py will run as a daemon on boot
* an arrangement of wireless adapter and hostapd, so that the device acts as an access point
* the Apache web server and a web page for displaying scanned images and instructions
* a [real-time clock](https://www.adafruit.com/products/264), to allow the Pi to keep time in the absence of a network connection

Because the Raspberry Pi only has two USB ports, this system uses a [powered USB hub](http://www.adafruit.com/products/961) to connect the cameras and wireless adapter.

Post-processing
---------------
Although it's not specific to this combination of hardware and software, the post-processing workflow I'm currently using is as follows.  (The scripts [odd.sh](misc/odd.sh) and [even.sh](misc/even.sh) copy the rotated rectos and versos to the sorted/ directory with sequential filenames; this can be necessary if the two cameras get out of sync with regard to filenames.  It also allows you not to rely on accurate timestamps on the cameras.)

        rsync -avz pi@raspberrypi.local:public_html/bookscan_201301180911 .
        cd bookscan_201301180911/ ; mkdir sorted
        cd left/ ; mogrify -rotate "270>" IMG* ; ~/Documents/code/scanner/odd.sh
        cd ../right/ ; mogrify -rotate "90>" IMG* ; ~/Documents/code/scanner/even.sh
Run [ScanTailor](http://scantailor.sourceforge.net/) on sorted/; rotation is no longer necessary, deskew as needed, select content and margins automatically if possible; TIFF output files go to sorted/out/

        cd ../sorted/out/
        for img in *.tif; do tesseract $img `basename -s .tif $img` hocr; done
Proof the OCR output (HTML files)

        pdfbeads *.tif > output.pdf
