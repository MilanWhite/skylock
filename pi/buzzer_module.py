"""
MH-FMD Buzzer Module
====================

This module provides easy control of the MH-FMD buzzer module for audio alerts
and notifications.

Prerequisites:
-------------
1. Install RPi.GPIO (usually pre-installed):
   sudo apt-get install python3-rpi.gpio

   Or use gpiozero (alternative):
   sudo apt-get install python3-gpiozero

Usage Example:
-------------
from buzzer_module import BuzzerManager

# Initialize buzzer on GPIO 17
buzzer = BuzzerManager(pin=17)

# Simple beep
buzzer.beep()

# Multiple beeps
buzzer.beep(times=3, duration=0.2, pause=0.1)

# Play a pattern
buzzer.beep_pattern([0.1, 0.1, 0.1, 0.3])  # Short-short-short-long (SOS)

# Play a melody (if passive buzzer)
buzzer.play_tone(440, 0.5)  # A note for 0.5 seconds
buzzer.play_melody([440, 494, 523], [0.3, 0.3, 0.5])  # A, B, C

# Continuous sound
buzzer.on()
time.sleep(1)
buzzer.off()

# Cleanup when done
buzzer.cleanup()

Common Patterns:
---------------
buzzer.success_sound()      # Success notification
buzzer.error_sound()        # Error notification
buzzer.warning_sound()      # Warning notification
buzzer.startup_sound()      # Startup melody

"""

import time
import RPi.GPIO as GPIO


class BuzzerManager:
    """
    Manager class for MH-FMD buzzer operations.

    Supports both active and passive buzzers with simple beeps,
    patterns, and melodies.
    """

    def __init__(self, pin=17, buzzer_type='active'):
        """
        Initialize the buzzer manager.

        Args:
            pin (int): GPIO pin number (BCM numbering)
            buzzer_type (str): 'active' or 'passive'

        Raises:
            ValueError: If invalid buzzer_type
        """

        self.pin = pin
        # Respect the requested buzzer type (default 'active')
        if buzzer_type not in ('active', 'passive'):
            raise ValueError("buzzer_type must be 'active' or 'passive'")
        self.buzzer_type = buzzer_type

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)

        # Confirmation message
        print(f"✓ Buzzer initialized on GPIO {self.pin} ({self.buzzer_type})")

    def on(self):
        """Turn buzzer on continuously."""
        GPIO.output(self.pin, GPIO.HIGH)

    # Convenience alias
    def turn_on(self):
        """Alias for on() to make API clearer for callers."""
        self.on()

    def off(self):
        """Turn buzzer off."""
        GPIO.output(self.pin, GPIO.LOW)

    # Convenience alias
    def turn_off(self):
        """Alias for off() to make API clearer for callers."""
        self.off()

    def beep(self, duration=0.1, times=1, pause=0.1):
        """
        Make beep sound(s).

        Args:
            duration (float): Length of each beep in seconds
            times (int): Number of beeps
            pause (float): Pause between beeps in seconds
        """
        for i in range(times):
            self.on()
            time.sleep(duration)
            self.off()
            if i < times - 1:  # Don't pause after last beep
                time.sleep(pause)

    def beep_custom(self, times, duration, pause=0.1):
        """Convenience wrapper that validates arguments and calls beep.

        Args:
            times (int): number of beeps (must be >=1)
            duration (float): seconds each beep lasts (must be >0)
            pause (float): pause between beeps in seconds (>=0)
        """
        # Basic validation and normalization
        try:
            times = int(times)
            duration = float(duration)
            pause = float(pause)
        except Exception:
            raise ValueError("times must be int-like, duration and pause must be numbers")

        if times < 1:
            raise ValueError("times must be >= 1")
        if duration <= 0:
            raise ValueError("duration must be > 0")
        if pause < 0:
            raise ValueError("pause must be >= 0")

        self.beep(duration=duration, times=times, pause=pause)

    def beep_pattern(self, pattern):
        """
        Play a beep pattern.

        Args:
            pattern (list): List of durations in seconds
                          e.g., [0.1, 0.1, 0.3] = short, short, long

        Example:
            buzzer.beep_pattern([0.1, 0.1, 0.1, 0.3, 0.3, 0.3, 0.1, 0.1, 0.1])  # SOS
        """
        for i, duration in enumerate(pattern):
            self.on()
            time.sleep(duration)
            self.off()
            if i < len(pattern) - 1:
                time.sleep(0.1)  # Short pause between beeps

    def cleanup(self):
        """Clean up GPIO resources."""
        self.off()
        GPIO.cleanup(self.pin)
        print("✓ Buzzer cleaned up")


# Example usage and testing
if __name__ == "__main__":
    """
    Test script to verify buzzer functionality.
    """
    import sys

    print("="*60)
    print("MH-FMD Buzzer Test")
    print("="*60)
    print()

    # Only active buzzer supported
    print("Using active buzzer (on/off control)")
    buzzer_type = 'active'

    # Ask for GPIO pin
    print("\nWhich GPIO pin is the buzzer connected to?")
    print("(Default: GPIO 17 = Physical Pin 11)")
    pin_input = input("Enter GPIO number [17]: ").strip()
    pin = int(pin_input) if pin_input else 17

    print()

    try:
        # Initialize buzzer
        buzzer = BuzzerManager(pin=pin, buzzer_type=buzzer_type)
        print()

        # Menu
        print("Select test:")
        print("1. Single beep")
        print("2. Multiple beeps")

        # No passive buzzer options available

        test_choice = input("\nEnter choice: ").strip()
        print()

        if test_choice == '1':
            print("Playing single beep...")
            buzzer.beep()

        elif test_choice == '2':
            # Prompt user for number of beeps and duration
            times_input = input("Enter number of beeps [3]: ").strip()
            duration_input = input("Enter duration of each beep in seconds [0.2]: ").strip()
            pause_input = input("Enter pause between beeps in seconds [0.2]: ").strip()

            times = int(times_input) if times_input else 3
            duration = float(duration_input) if duration_input else 0.2
            pause = float(pause_input) if pause_input else 0.2

            print(f"Playing {times} beeps, {duration}s each, {pause}s pause...")
            buzzer.beep_custom(times=times, duration=duration, pause=pause)

        else:

            print("Invalid or unsupported choice")

        print("\n" + "="*60)
        print("Test complete!")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nTest interrupted")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check wiring connections")
        print("2. Verify GPIO pin number")
        print("3. Make sure buzzer is getting power")

    finally:
        try:
            buzzer.cleanup()
        except:
            GPIO.cleanup()
        print()