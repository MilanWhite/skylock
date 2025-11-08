#!/usr/bin/env python3
"""
Simple buzzer GPIO test script for active buzzers (on/off control).

Run on the Raspberry Pi with root privileges (RPi.GPIO usually requires sudo):

sudo python3 buzzer_test.py --pin 17 --test beep

Options:
  --pin   BCM pin number (default 17)
  --test  beep | pattern | alarm | onoff

This script will toggle the pin and print actions so you can confirm wiring and
that the GPIO pin responds.
"""

import time
import argparse

try:
    import RPi.GPIO as GPIO
except Exception as e:
    print("Error importing RPi.GPIO:", e)
    print("This script must be run on a Raspberry Pi with RPi.GPIO installed.")
    raise


def beep(pin, duration=0.2, times=1, pause=0.1):
    for i in range(times):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)
        if i < times - 1:
            time.sleep(pause)


def pattern(pin):
    # SOS-style short/long pattern
    seq = [0.1, 0.1, 0.1, 0.3, 0.3, 0.3, 0.1, 0.1, 0.1]
    for d in seq:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(d)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.1)


def alarm(pin, duration=3.0):
    end = time.time() + duration
    while time.time() < end:
        beep(pin, duration=0.15)
        time.sleep(0.15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple active-buzzer GPIO test')
    parser.add_argument('--pin', type=int, default=17, help='BCM GPIO pin number (default 17)')
    parser.add_argument('--test', choices=['beep', 'pattern', 'alarm', 'onoff'], default='beep')
    args = parser.parse_args()

    pin = args.pin

    print(f"Using BCM pin {pin}. Make sure your buzzer's negative is connected to GND and positive to this pin via appropriate resistor if needed.")
    print("Note: run with sudo on a Raspberry Pi: sudo python3 buzzer_test.py --pin 17 --test beep")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)

    try:
        if args.test == 'beep':
            print('Playing 3 beeps...')
            beep(pin, duration=0.2, times=3, pause=0.2)

        elif args.test == 'pattern':
            print('Playing SOS pattern...')
            pattern(pin)

        elif args.test == 'alarm':
            print('Playing alarm for 3 seconds...')
            alarm(pin, duration=3.0)

        elif args.test == 'onoff':
            print('Turning buzzer ON for 2 seconds...')
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(2)
            print('Turning buzzer OFF')
            GPIO.output(pin, GPIO.LOW)

        print('Test complete')

    except KeyboardInterrupt:
        print('\nTest interrupted')

    finally:
        GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()
        print('GPIO cleaned up')
