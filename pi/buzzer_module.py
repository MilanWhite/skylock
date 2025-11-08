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
        self.buzzer_type = 'active'

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)

        print(f"✓ Buzzer initialized on GPIO {self.pin} (active)")

    def on(self):
        """Turn buzzer on continuously."""
        GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        """Turn buzzer off."""
        GPIO.output(self.pin, GPIO.LOW)

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

    def play_tone(self, frequency, duration=0.5):
        """
        Play a specific tone.

        Note: passive-tone generation is not supported. For active buzzers
        we emulate a tone by a short on/off beep of the requested duration.

        Args:
            frequency (int|str): Ignored for active buzzers (kept for API
                compatibility).
            duration (float): Duration in seconds
        """
        # For active buzzer, just turn on for duration
        self.on()
        time.sleep(duration)
        self.off()

    def play_melody(self, notes, durations):
        """
        Play a melody.

        Note: real melodies require a passive buzzer (PWM). For active
        buzzers we fall back to a sequence of beeps using the durations
        provided.

        Args:
            notes (list): Ignored for active buzzers (kept for API compatibility)
            durations (list): List of durations in seconds
        """
        if len(durations) == 0:
            return

        # Play a sequence of beeps for each duration
        for duration in durations:
            self.beep(duration=duration)
            time.sleep(0.05)

    # ============================================================
    # Pre-defined Sound Patterns
    # ============================================================

    def success_sound(self):
        """Play success notification sound."""
        # Quick double beep
        self.beep(0.1, times=2, pause=0.05)

    def error_sound(self):
        """Play error notification sound."""
        # Long beep
        self.beep(0.5)

    def warning_sound(self):
        """Play warning notification sound."""
        # Three quick beeps
        self.beep(0.1, times=3, pause=0.1)

    def startup_sound(self):
        """Play startup/boot sound."""
        # Two beeps
        self.beep(0.1, times=2, pause=0.2)

    def sos_pattern(self):
        """Play SOS pattern (... --- ...)."""
        pattern = [
            0.1, 0.1, 0.1,  # S (short-short-short)
            0.3, 0.3, 0.3,  # O (long-long-long)
            0.1, 0.1, 0.1   # S (short-short-short)
        ]
        self.beep_pattern(pattern)

    def alarm_sound(self, duration=3):
        """
        Play alarm sound for specified duration.

        Args:
            duration (float): Total duration in seconds
        """
        # Rapid beeping for active buzzer
        beep_count = max(1, int(duration / 0.3))
        self.beep(0.15, times=beep_count, pause=0.15)

    def notification_sound(self, level='info'):
        """
        Play notification sound based on level.

        Args:
            level (str): 'info', 'success', 'warning', or 'error'
        """
        sounds = {
            'info': lambda: self.beep(0.1),
            'success': self.success_sound,
            'warning': self.warning_sound,
            'error': self.error_sound
        }

        sound_func = sounds.get(level.lower(), lambda: self.beep(0.1))
        sound_func()

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
        print("3. Success sound")
        print("4. Error sound")
        print("5. Warning sound")
        print("6. Startup sound")
        print("7. SOS pattern")
        print("8. Alarm (3 seconds)")

        # No passive buzzer options available

        test_choice = input("\nEnter choice: ").strip()
        print()

        if test_choice == '1':
            print("Playing single beep...")
            buzzer.beep()

        elif test_choice == '2':
            print("Playing 3 beeps...")
            buzzer.beep(times=3, duration=0.2, pause=0.2)

        elif test_choice == '3':
            print("Playing success sound...")
            buzzer.success_sound()

        elif test_choice == '4':
            print("Playing error sound...")
            buzzer.error_sound()

        elif test_choice == '5':
            print("Playing warning sound...")
            buzzer.warning_sound()

        elif test_choice == '6':
            print("Playing startup sound...")
            buzzer.startup_sound()

        elif test_choice == '7':
            print("Playing SOS pattern...")
            buzzer.sos_pattern()

        elif test_choice == '8':
            print("Playing alarm for 3 seconds...")
            buzzer.alarm_sound(duration=3)

        else:
            # All melody/tone-specific features were removed; keep other options
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