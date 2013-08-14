#!/usr/bin/python

# bookscanner.py
#
# Copyright 2013 Ben Steinberg <benjamin_steinberg@harvard.edu>
# Harvard Library, Office for Scholarly Communication

# derived from 
# https://raw.github.com/markvdb/diybookscanner/master/misc/test_keypedal.sh
# by Mark Van den Borre <mark@markvdb.be>

# TODO: what happens if cameras shut down? now checking in inner loop --
#       does set_ndfilter() work?
#       error-checking after calls to Popen?  raise exceptions?
#       what should this do when it gets a signal from the OS?  now handling Ctrl-C in outer loop.
#       set the outer loop to shut down the pi after some amount of inactivity?
#
## Ben Steinberg <benjamin_steinberg@harvard.edu>

from time import time, sleep
import sys
from datetime import datetime
from subprocess import Popen, PIPE
from os import makedirs, chdir, utime, chmod, walk, chown, execl
from os.path import join
import RPi.GPIO as GPIO
import re
import usb # 1.0, cloned from git://github.com/walac/pyusb.git -- Debian has 0.4.x
import lcd

PTPCAM =        '/usr/local/bin/ptpcam'
TMOUT =         15
PIN =           18
SHOTS =         0

SHORTPAUSE =    0.5
PAUSE =         3
LONGPAUSE =     5
DEBOUNCEPAUSE = 0.05

DLFACTOR =      1.5 # multiplier for download time
SCANDIRPREFIX = '/home/pi/public_html/bookscan_'
CANON =         1193 # decimal from hex value from lsusb or http://www.pcidatabase.com/vendors.php
BRAND =         CANON
SHOTPARAMS =    'set_iso_real(100) ; set_av96(384) ; shoot()' # change exposure here

MARQUEETEXT =   'SSID: bookscanner -- http://192.168.7.1/'

def marquee_generator(string):
    padding = " " * 15
    long_string = padding + string + padding
    length = len(long_string)
    divisor = len(padding) + len(string)
    counter = 0
    while (True):
        i = length % divisor
        if counter % 5 == 0:
            length += 1
        counter += 1
        yield long_string[i:i+20]

marquee = marquee_generator(MARQUEETEXT)

def main():
    lcd.clear()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN, GPIO.IN)

    outer_loop()    

def restart_program():
    # from http://www.daniweb.com/software-development/python/code/260268/restart-your-python-program
    python = sys.executable
    execl(python, python, * sys.argv)

def cmdoutput(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out.rstrip()

def detect_cams():
    lcd.display(4, "detecting cameras...", 1)
    global LEFTCAM, RIGHTCAM, LEFTCAMLONG, RIGHTCAMLONG, GPHOTOCAM1, GPHOTOCAM2
    #CAMS = cmdoutput("gphoto2 --auto-detect|grep usb| wc -l")
    CAMS = camera_count(BRAND)
    if CAMS == 2:
        GPHOTOCAM1 = cmdoutput("gphoto2 --auto-detect|grep usb|sed -e 's/.*Camera *//g'|head -n1")
        GPHOTOCAM2 = cmdoutput("gphoto2 --auto-detect|grep usb|sed -e 's/.*Camera *//g'|tail -n1")
        print GPHOTOCAM1, "is gphotocam1"
        print GPHOTOCAM2, "is gphotocam2"
    
        GPHOTOCAM1ORIENTATION=cmdoutput("gphoto2 --port " + GPHOTOCAM1 + " --get-config /main/settings/ownername|grep Current|sed -e's/.*\ //'")
        GPHOTOCAM2ORIENTATION=cmdoutput("gphoto2 --port " + GPHOTOCAM2 + " --get-config /main/settings/ownername|grep Current|sed -e's/.*\ //'")
        print "gphotocam1orientation is", GPHOTOCAM1ORIENTATION
        print "gphotocam2orientation is", GPHOTOCAM2ORIENTATION

        CAM1=cmdoutput("echo " + GPHOTOCAM1 + "|sed -e 's/.*,//g'")
        CAM2=cmdoutput("echo " + GPHOTOCAM2 + "|sed -e 's/.*,//g'")
        print "Detected 2 camera devices:", GPHOTOCAM1, "and", GPHOTOCAM2
    else: 
        print "Number of camera devices does not equal 2. Giving up."
        lcd.display(4, "", 1)
        lcd.display(2, "CAMERAS OFF.", 1)
        lcd.display(3, "RESTARTING...", 1)
        sleep(PAUSE)
        restart_program()

    if GPHOTOCAM1ORIENTATION == "left":
        LEFTCAM=cmdoutput("echo " + GPHOTOCAM1 + "|sed -e 's/.*,//g'")
        LEFTCAMLONG=GPHOTOCAM1
    elif GPHOTOCAM1ORIENTATION == "right":
        RIGHTCAM=cmdoutput("echo " + GPHOTOCAM1 + "|sed -e 's/.*,//g'")
        RIGHTCAMLONG=GPHOTOCAM1
    else:
        lcd.display(2, "OWNER NAME NOT SET.", 1)
        lcd.display(3, "RESTARTING...", 1)
        sleep(PAUSE)
        print GPHOTOCAM1, "owner name is neither set to left or right. Please configure that before continuing."
        restart_program()

    if GPHOTOCAM2ORIENTATION == "left":
        LEFTCAM=cmdoutput("echo " + GPHOTOCAM2 + "|sed -e 's/.*,//g'")
        LEFTCAMLONG=GPHOTOCAM2
    elif GPHOTOCAM2ORIENTATION == "right":
        RIGHTCAM=cmdoutput("echo " + GPHOTOCAM2 + "| sed -e 's/.*,//g'")
        RIGHTCAMLONG=GPHOTOCAM2
    else:
        lcd.display(2, "OWNER NAME NOT SET.", 1)
        lcd.display(3, "RESTARTING...", 1)
        sleep(PAUSE)
        print GPHOTOCAM1, "owner name is neither set to left or right. Please configure that before continuing."
        restart_program()

def delete_from_cams():
    lcd.display(3, "deleting from", 1)
    lcd.display(4, "cameras...", 1)
    for cam in LEFTCAM, RIGHTCAM:
        print "deleting existing images from SD card on " + cam
        cmd = PTPCAM + " --dev=" + cam + " -D; true"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(SHORTPAUSE)
    lcd.display(4, "", 1)

def switch_to_record_mode():
    lcd.display(4, "switching mode...", 1)
    print "Switching cameras to record mode..."
    print "LEFTCAM is", LEFTCAM, "and RIGHTCAM is", RIGHTCAM
    for cam in LEFTCAM, RIGHTCAM:
        print "Switching camera", cam, "to record mode and sleeping 1 second..."
        cmd=PTPCAM + " --dev=" + cam + " --chdk='mode 1' > /dev/null 2>&1 && sleep 1s"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    sleep(PAUSE)

def set_zoom():
    lcd.display(4, "setting zoom...", 1)
    # TODO: make less naive about zoom setting (check before and after setting, ...)
    print "Setting zoom..."
    for cam in LEFTCAM, RIGHTCAM:
        print "Setting camera", cam, "zoom to 3..."
        lcd.display(4, "setting cam " + cam + " zoom", 1)
        # lua set_zoom() makes one camera shut down, looks like, so we're clicking:
        cmd=PTPCAM + " --dev=" + cam + " --chdk='lua while(get_zoom()<3) do click(\"zoom_in\") end'"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(PAUSE)
        cmd=PTPCAM + " --dev=" + cam + " --chdk='lua while(get_zoom()>3) do click(\"zoom_out\") end'"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(PAUSE)
    sleep(PAUSE)

def flash_off():
    lcd.display(4, "turning flash off...", 1)
    print "Switching flash off..."
    for cam in LEFTCAM, RIGHTCAM:
        cmd=PTPCAM + " --dev=" + cam + " --chdk='lua while(get_flash_mode()<2) do click(\"right\") end'"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(SHORTPAUSE)

def download_from_cams():
    lcd.display(3, "downloading...", 1)
    TIMESTAMP=datetime.now().strftime("%Y%m%d%H%M")
    # gphoto2 processes end with -1 unexpected result even though everything seems to be fine -> hack: true gives exit status 0
    # ptpcam downloads with bad file creation date and permissions....
    for side in "left", "right":
        makedirs(SCANDIRPREFIX+TIMESTAMP+"/"+side)
        chown(SCANDIRPREFIX+TIMESTAMP+"/"+side, 1000, 1000)
        chmod(SCANDIRPREFIX+TIMESTAMP+"/"+side, 0755)
    chown(SCANDIRPREFIX+TIMESTAMP, 1000, 1000)
    chmod(SCANDIRPREFIX+TIMESTAMP, 0755)

    # previous attempts used gphoto, then ptpcam en masse; then tried listing
    # then downloading one at a time with ptpcam; now back to bulk, but waiting
    # an amount of time proportional to the number of files
    for pair in [LEFTCAM, "left"], [RIGHTCAM, "right"]:
        print "Downloading images from", pair[0], "..."
        chdir(SCANDIRPREFIX+TIMESTAMP+"/"+pair[1])
        cmd = PTPCAM + " --dev=" + pair[0] + " -L | grep 0x | wc -l"
        numfiles = cmdoutput(cmd)
        print "I see " + numfiles + " images on " + pair[0]
        lcd.display(4, numfiles + " files from " + pair[1], 1)
        cmd = PTPCAM + " --dev=" + pair[0] + " -G ; true"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleeptime = DLFACTOR * int(numfiles)
        print "sleeping " + str(sleeptime) + " seconds"
        sleep(sleeptime)
    sleep(LONGPAUSE)

    # timestamp and perms are not set correctly on the files we get from the camera....
    counter = 0
    for root, dirs, files in walk(SCANDIRPREFIX+TIMESTAMP):
        for filename in files:
            thisfile = join(root, filename)
            utime(thisfile, None)
            chown(thisfile, 33, 33)
            chmod(thisfile, 0744)
            counter += 1
    print "Adjusted " + str(counter) + " files"

def set_iso():
    lcd.display(4, "setting ISO...", 1)
    for cam in LEFTCAM, RIGHTCAM:
        print "Setting ISO mode to 1 for camera", cam
        cmd=PTPCAM + " --dev=" + cam + " --chdk=\"lua set_iso_real(50)\""
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(SHORTPAUSE)
    lcd.display(4, "", 1)

def set_ndfilter():
    lcd.display(4, "setting ND filter...", 1)
    for cam in LEFTCAM, RIGHTCAM:
        print "Disabling neutral density filter for", cam, "-- see http://chdk.wikia.com/wiki/ND_Filter"
        cmd=PTPCAM + " --dev=" + cam + "--chdk=\"luar set_nd_filter(2)\""
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(SHORTPAUSE)
    lcd.display(4, "", 1)

def outer_loop():
    lcd.clear()

    global SHOTS
    # debounce code from http://www.cl.cam.ac.uk/projects/raspberrypi/tutorials/robot/buttons_and_switches/
    lcd.display(2, "TURN ON CAMERAS,", 1)
    lcd.display(3, "TAP PEDAL TO START", 1)
    print "Starting outer foot pedal loop..."
    prev_input = 0
    firstloop = 1
    # start = time()
    while True:
        try:
            input = GPIO.input(PIN)
            if ((not prev_input) and input):
                if (firstloop != 1):
                    print("Button pressed")
                    lcd.display(2, "starting up", 2)
                    lcd.display(3, "PLEASE WAIT", 2)
                    detect_cams()
                    # delete_from cams confuses ptpcam -> do that at the end
                    switch_to_record_mode()
                    set_zoom()
                    flash_off()
                    set_iso()
                    set_ndfilter()
                    SHOTS = 0
                    inner_loop()
                    # start = time()
                    lcd.display(2, "TURN ON CAMERAS,", 1)
                    lcd.display(3, "TAP PEDAL TO START", 1)
                    print "Rejoining outer foot pedal loop..."
                firstloop = 0
            prev_input = input
            # slight pause to debounce
            sleep(DEBOUNCEPAUSE)
        except KeyboardInterrupt:
            lcd.clear()
            lcd.display(2, "GOODBYE", 2)
            sleep(PAUSE)
            lcd.clear()
            print "Quitting."
            sys.exit()
        text = marquee.next()
        lcd.display(1, text, 1)

def inner_loop():
    global SHOTS
    lcd.clear()

    lcd.display(2, "", 1)
    lcd.display(3, "TAP TO SHOOT", 2)
    lcd.display(4, "ready", 1)
    print "Starting inner foot pedal loop..."
    start = time()
    prev_input = 0
    firstloop = 1
    while True:
        input = GPIO.input(PIN)
        if ((not prev_input) and input):
            if (firstloop != 1):
                print("Button pressed")
                shoot()
                SHOTS += 1
                lcd.display(2, str(SHOTS / 2), 1)
                start = time()
            firstloop = 0
        prev_input = input
        #slight pause to debounce
        sleep(DEBOUNCEPAUSE)

        # check that a camera hasn't turned off
        # can we do this more quickly?  it's interfering with the pedal.
        #cmdoutput("lsusb | grep Canon | wc -l") == "2"                                      # 1.16 sec
        #cmdoutput(PTPCAM + " -l | grep 0x | wc -l") == "2"                                  # 0.42 sec
        #cmdoutput("gphoto2 --auto-detect|grep usb|sed -e 's/.*Camera *//g' | wc -l") == "2" # 0.36 sec
        #cmdoutput("gphoto2 --auto-detect | grep Camera | wc -l") == "2"                     # 0.34 sec, still too long
        if camera_count(BRAND) == 2:                                       # 0.58 sec from command line, faster inside the program? yes!
            pass
        else:
            print "Number of camera devices does not equal 2. Try again."
            for cam in LEFTCAM, RIGHTCAM:
                cmd=PTPCAM + " --dev=" + cam + " --chdk='lua play_sound(3)'"
                p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            lcd.display(2, "A CAMERA IS OFF.", 1)
            lcd.display(3, "RESTARTING...", 1)
            lcd.display(4, "", 1)
            sleep(PAUSE)
            return

        now = time()
        if now - start > TMOUT:
            lcd.display(2, "", 1)
            lcd.display(3, "TIMEOUT", 2)
            lcd.display(4, "", 1)
            print "Foot pedal not pressed for", TMOUT, "seconds."
            download_from_cams()
            delete_from_cams()
            print "Quitting inner loop"
            return
        text = marquee.next()
        lcd.display(1, text, 1)


def camera_count(brand):
    counter = 0
    for dev in usb.core.find(find_all=True):
        if dev.idVendor == brand:
            counter += 1
    return counter

def shoot():
    global SHOTS
    lcd.display(3, "WAIT", 2)
    lcd.display(4, "shooting", 1)
    print "Shooting with cameras", LEFTCAM, "(left) and ", RIGHTCAM, " (right)"
    for cam in LEFTCAM, RIGHTCAM:
        cmd=PTPCAM + " --dev=" + cam + " --chdk='lua " + SHOTPARAMS + "'"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        sleep(SHORTPAUSE * 2)
    sleep(SHORTPAUSE * 2) # necessary?
    lcd.display(4, "ready", 1)
    lcd.display(3, "TAP TO SHOOT", 2)
    SHOTS += 1

main()


