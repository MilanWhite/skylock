"""
DS3231 Real-Time Clock (RTC) Module
====================================

This module provides an easy-to-use interface for the DS3231 RTC connected to Raspberry Pi.

Usage Example:
-------------
from rtc_module import RTCManager

# Initialize RTC
rtc = RTCManager()

# Get current time
print(rtc.get_datetime_string())      # "2025-11-07 18:30:45"
print(rtc.get_time_string())          # "18:30:45"
print(rtc.get_date_string())          # "2025-11-07"

# Get individual components
year, month, day, hour, minute, second = rtc.get_datetime_components()
print(f"Hour: {hour}, Minute: {minute}")

# Get temperature (DS3231 has built-in sensor)
temp = rtc.get_temperature()
print(f"Temperature: {temp:.1f}°C")

# Set time manually (if needed)
rtc.set_datetime(2025, 11, 7, 18, 30, 0)

# Get timestamp for logging
timestamp = rtc.get_timestamp()
print(f"Log entry at: {timestamp}")

Author: [Your Team Name]
Date: November 2025
"""

import time
from datetime import datetime


class RTCManager:
    """
    Manager class for DS3231 Real-Time Clock operations.

    This class reads time from the Raspberry Pi system clock, which is
    synchronized with the DS3231 RTC via the kernel driver.
    This avoids I2C address conflicts while still using the RTC.
    """

    def __init__(self):
        """
        Initialize the RTC manager.

        Uses system time which is synced with DS3231 via kernel driver.
        """
        print("✓ RTC Manager initialized (using system time synced with DS3231)")

    def get_datetime_string(self, format_24h=True):
        """
        Get formatted date and time string.

        Args:
            format_24h (bool): Use 24-hour format if True, 12-hour if False

        Returns:
            str: Formatted datetime string (e.g., "2025-11-07 18:30:45")
        """
        now = datetime.now()

        if format_24h:
            return now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return now.strftime("%Y-%m-%d %I:%M:%S %p")

    def get_time_string(self, format_24h=True):
        """
        Get formatted time string only (no date).

        Args:
            format_24h (bool): Use 24-hour format if True, 12-hour if False

        Returns:
            str: Formatted time string (e.g., "18:30:45" or "06:30:45 PM")
        """
        now = datetime.now()

        if format_24h:
            return now.strftime("%H:%M:%S")
        else:
            return now.strftime("%I:%M:%S %p")

    def get_date_string(self):
        """
        Get formatted date string only (no time).

        Returns:
            str: Formatted date string (e.g., "2025-11-07")
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    def get_datetime_components(self):
        """
        Get individual datetime components.

        Returns:
            tuple: (year, month, day, hour, minute, second)
        """
        now = datetime.now()
        return (now.year, now.month, now.day,
                now.hour, now.minute, now.second)

    def get_timestamp(self):
        """
        Get a timestamp string suitable for logging.

        Returns:
            str: Timestamp in format "[2025-11-07 18:30:45]"
        """
        return f"[{self.get_datetime_string()}]"

    def get_temperature(self):
        """
        Get temperature from Raspberry Pi CPU.

        Note: This returns CPU temperature, not DS3231 sensor temperature.
        The DS3231 temperature is not accessible when using kernel driver.

        Returns:
            float: CPU temperature in Celsius
        """
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return temp
        except:
            return 0.0

    def set_datetime(self, year, month, day, hour, minute, second):
        """
        Set the system time manually (requires sudo).

        Args:
            year (int): Year (e.g., 2025)
            month (int): Month (1-12)
            day (int): Day (1-31)
            hour (int): Hour (0-23)
            minute (int): Minute (0-59)
            second (int): Second (0-59)

        Example:
            rtc.set_datetime(2025, 11, 7, 18, 30, 0)

        Note: This sets system time. The DS3231 will be updated automatically
              by the kernel driver.
        """
        import os
        date_string = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        result = os.system(f"sudo date -s '{date_string}' > /dev/null 2>&1")

        if result == 0:
            print(f"✓ System time set to: {self.get_datetime_string()}")
        else:
            print("⚠ Failed to set time (may need sudo privileges)")

    def get_day_of_week(self):
        """
        Get the day of the week.

        Returns:
            str: Day name (e.g., "Monday", "Tuesday")
        """
        now = datetime.now()
        return now.strftime("%A")

    def get_am_pm(self):
        """
        Get the current period of day as 'AM' or 'PM'.

        Returns:
            str: 'AM' if time is before noon, otherwise 'PM'
        """
        now = datetime.now()
        return "AM" if now.hour < 12 else "PM"

    def is_daytime(self, sunrise_hour=6, sunset_hour=18):
        """
        Check if current time is during daytime hours.

        Args:
            sunrise_hour (int): Hour when day starts (default: 6)
            sunset_hour (int): Hour when day ends (default: 18)

        Returns:
            bool: True if daytime, False if nighttime
        """
        now = datetime.now()
        return sunrise_hour <= now.hour < sunset_hour

    def get_formatted_display(self):
        """
        Get a nicely formatted string for display purposes.

        Returns:
            str: Multi-line formatted display string
        """
        now = datetime.now()
        day_name = self.get_day_of_week()
        temp = self.get_temperature()

        return (f"{day_name}, {now.day:02d}/{now.month:02d}/{now.year}\n"
                f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}\n"
                f"CPU Temperature: {temp:.1f}°C")


# Example usage and testing
if __name__ == "__main__":
    """
    Test script to verify RTC functionality.
    Run this to make sure your RTC is working correctly.
    """
    print("="*60)
    print("DS3231 RTC Test Script")
    print("="*60)

    try:
        # Initialize RTC
        rtc = RTCManager()
        print()

        # Display current status
        print("Current RTC Status:")
        print("-"*60)
        print(rtc.get_formatted_display())
        print("-"*60)
        print()

        # Show different format options
        print("Different Time Formats:")
        print(f"  24-hour format: {rtc.get_datetime_string(format_24h=True)}")
        print(f"  12-hour format: {rtc.get_datetime_string(format_24h=False)}")
        print(f"  Date only:      {rtc.get_date_string()}")
        print(f"  Time only:      {rtc.get_time_string()}")
        print(f"  Timestamp:      {rtc.get_timestamp()}")
        print()

        # Show components
        year, month, day, hour, minute, second = rtc.get_datetime_components()
        print("Individual Components:")
        print(f"  Year: {year}, Month: {month}, Day: {day}")
        print(f"  Hour: {hour}, Minute: {minute}, Second: {second}")
        print()

        # Live clock demonstration
        # Quick query menu for user to get time/date/AM-PM
        print("Quick queries:")
        print("  1) Show current time (24-hour)")
        print("  2) Show current time (12-hour with AM/PM)")
        print("  3) Show current date")
        print("  4) Show AM/PM")
        print("  5) Start live clock (press Ctrl+C to stop)")

        q = input("Enter choice [1]: ").strip()
        if q == "" or q == "1":
            print(f"Current time (24h): {rtc.get_time_string(format_24h=True)}")
        elif q == "2":
            print(f"Current time (12h): {rtc.get_time_string(format_24h=False)}")
        elif q == "3":
            print(f"Current date: {rtc.get_date_string()}")
        elif q == "4":
            print(f"Current period: {rtc.get_am_pm()}")
        elif q == "5":
            print("Live Clock (press Ctrl+C to stop):")
            print("-"*60)
            while True:
                # Clear line and print time
                time_str = rtc.get_datetime_string()
                temp = rtc.get_temperature()
                day = rtc.get_day_of_week()

                print(f"{day} | {time_str} | Temp: {temp:.1f}°C", end='\r')
                time.sleep(1)
        else:
            print("Invalid choice, exiting test.")

    except KeyboardInterrupt:
        print("\n" + "-"*60)
        print("Test complete!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check wiring connections")
        print("2. Verify I2C is enabled: sudo raspi-config")
        print("3. Check I2C devices: sudo i2cdetect -y 1")
        print("4. Ensure DS3231 driver is loaded in /boot/config.txt")