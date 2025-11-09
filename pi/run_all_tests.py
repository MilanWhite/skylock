#!/usr/bin/env python3
"""
Run quick tests across pi/ modules.

Features:
- Syntax-check all .py files in the `pi/` folder.
- Optionally run safe hardware checks for buzzer, compass, and rtc when
  running on a Raspberry Pi with the --hardware flag.

Usage examples:
  # Syntax-check all pi/ files
  python3 pi/run_all_tests.py

  # Syntax-check and run hardware checks (will attempt to access I2C/GPIO)
  sudo python3 pi/run_all_tests.py --hardware --buzzer-pin 17

Notes:
- Hardware checks will only run if --hardware is passed. They attempt to
  instantiate the hardware managers and call read methods; they catch and
  report exceptions so they are non-destructive.
- The runner avoids importing `app.py` (which runs a fullscreen loop) and
  instead performs a syntax check on it.
"""

import os
import sys
import glob
import time
import argparse
import importlib.util

ROOT = os.path.dirname(__file__)
PI_DIR = ROOT

HARDWARE_MODULES = {
    'buzzer_module.py': 'buzzer',
    'compass_module.py': 'compass',
    'rtc_module.py': 'rtc'
}


def syntax_check(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        compile(src, path, 'exec')
        print(f"OK  - Syntax OK: {os.path.basename(path)}")
        return True
    except Exception as e:
        print(f"ERR - Syntax error in {os.path.basename(path)}: {e}")
        return False


def run_buzzer_test(pin=17):
    print('\n--- Buzzer hardware test ---')
    try:
        from buzzer_module import BuzzerManager
    except Exception as e:
        print('Could not import buzzer_module:', e)
        return False

    try:
        print(f'Initializing buzzer on BCM pin {pin}...')
        bz = BuzzerManager(pin=pin)
        print('Beep pattern: 3 short beeps')
        bz.beep(times=3, duration=0.15, pause=0.12)
        time.sleep(0.2)
        print('ON for 0.5s')
        bz.on(); time.sleep(0.5); bz.off()
        bz.cleanup()
        print('Buzzer test completed')
        return True
    except Exception as e:
        print('Buzzer test error:', e)
        return False


def run_compass_test():
    print('\n--- Compass hardware test ---')
    try:
        from compass_module import CompassManager
    except Exception as e:
        print('Could not import compass_module:', e)
        return False

    try:
        c = CompassManager()
        heading = c.get_heading()
        print(f'Heading: {heading:.2f}°')
        mag = c.get_magnetic_field()
        print(f'Mag x,y,z: {mag[0]:.2f}, {mag[1]:.2f}, {mag[2]:.2f}')
        acc = c.get_acceleration()
        print(f'Accel x,y,z: {acc[0]:.2f}, {acc[1]:.2f}, {acc[2]:.2f}')
        return True
    except Exception as e:
        print('Compass test error:', e)
        return False


def run_rtc_test():
    print('\n--- RTC hardware test ---')
    try:
        from rtc_module import RTCManager
    except Exception as e:
        print('Could not import rtc_module:', e)
        return False

    try:
        r = RTCManager()
        print('Datetime:', r.get_datetime_string())
        print('Temperature:', f"{r.get_temperature():.1f}°C")
        return True
    except Exception as e:
        print('RTC test error:', e)
        return False


def main():
    parser = argparse.ArgumentParser(description='Run tests for pi/ modules')
    parser.add_argument('--hardware', action='store_true', help='Allow hardware tests (GPIO/I2C)')
    parser.add_argument('--buzzer-pin', type=int, default=17, help='BCM pin for buzzer tests (default 17)')
    parser.add_argument('--only', choices=['buzzer','compass','rtc','all','syntax'], default='syntax', help='Which tests to run')
    args = parser.parse_args()

    print('Scanning pi/ for Python files...')
    py_files = sorted(glob.glob(os.path.join(PI_DIR, '*.py')))

    # Syntax check all files
    print('\nRunning syntax checks:')
    syntax_results = {}
    for p in py_files:
        # Skip helper test runner itself when checking if running it
        if os.path.basename(p) == os.path.basename(__file__):
            continue
        syntax_results[p] = syntax_check(p)

    if args.only == 'syntax':
        print('\nSyntax check complete.')
        ok = all(syntax_results.values())
        sys.exit(0 if ok else 2)

    # Hardware tests
    if not args.hardware:
        print('\nHardware tests skipped. Re-run with --hardware to enable them.')
        sys.exit(0)

    print('\nHardware tests enabled (attempting to access GPIO/I2C)')

    if args.only in ('buzzer', 'all'):
        run_buzzer_test(pin=args.buzzer_pin)

    if args.only in ('compass', 'all'):
        run_compass_test()

    if args.only in ('rtc', 'all'):
        run_rtc_test()

    print('\nAll requested tests finished.')


if __name__ == '__main__':
    main()
