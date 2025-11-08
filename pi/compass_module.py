"""
Adafruit 10-DOF IMU Compass Module
===================================

This module provides compass heading and orientation data from the Adafruit 10-DOF IMU breakout.
The 10-DOF includes: LSM303 (accelerometer + magnetometer), L3GD20 (gyroscope), and BMP280 (barometer).

For compass functionality, we primarily use the magnetometer (LSM303).

Usage Example:
-------------
from compass_module import CompassManager

# Initialize compass
compass = CompassManager()

# Get heading
heading = compass.get_heading()
print(f"Heading: {heading:.1f}°")

# Get cardinal direction
direction = compass.get_cardinal_direction()
print(f"Direction: {direction}")  # e.g., "N", "NE", "E", etc.

# Get all sensor data
data = compass.get_all_data()
print(f"Heading: {data['heading']:.1f}°")
print(f"Direction: {data['direction']}")
print(f"Magnetic field: X={data['mag_x']:.2f} Y={data['mag_y']:.2f} Z={data['mag_z']:.2f} µT")

# Check if heading is stable
if compass.is_heading_stable():
    print("Compass reading is stable")

Calibration:
-----------
For best results, calibrate the magnetometer:
    compass = CompassManager()
    compass.calibrate()
    # Follow on-screen instructions to rotate sensor

"""

import time
import math
import board
import busio
from adafruit_lsm303dlh_mag import LSM303DLH_Mag
from adafruit_lsm303_accel import LSM303_Accel


class CompassManager:
    """
    Manager class for compass operations using the LSM303 magnetometer.

    This class provides methods to read compass heading, cardinal directions,
    and raw magnetometer data from the Adafruit 10-DOF IMU breakout.
    """

    def __init__(self, calibration_offset=(0, 0, 0)):
        """
        Initialize the compass manager.

        Args:
            calibration_offset (tuple): (x, y, z) calibration offsets for magnetometer

        Raises:
            RuntimeError: If sensors cannot be initialized
        """
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.mag = LSM303DLH_Mag(self.i2c)
            self.accel = LSM303_Accel(self.i2c)

            # Calibration offsets (set after calibration)
            self.cal_offset_x = calibration_offset[0]
            self.cal_offset_y = calibration_offset[1]
            self.cal_offset_z = calibration_offset[2]

            # For heading stability detection
            self.previous_readings = []
            self.stability_window = 5

            print("✓ Compass initialized successfully")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize compass: {e}")

    def get_magnetic_field(self):
        """
        Get raw magnetometer readings.

        Returns:
            tuple: (x, y, z) magnetic field values in µT (microtesla)
        """
        mag_x, mag_y, mag_z = self.mag.magnetic

        # Apply calibration offsets
        mag_x -= self.cal_offset_x
        mag_y -= self.cal_offset_y
        mag_z -= self.cal_offset_z

        return (mag_x, mag_y, mag_z)

    def get_acceleration(self):
        """
        Get accelerometer readings.

        Returns:
            tuple: (x, y, z) acceleration values in m/s²
        """
        return self.accel.acceleration

    def get_heading(self, use_tilt_compensation=False):
        """
        Calculate compass heading from magnetometer data.

        Args:
            use_tilt_compensation (bool): Apply tilt compensation using accelerometer

        Returns:
            float: Heading in degrees (0-360), where 0° is North
        """
        mag_x, mag_y, mag_z = self.get_magnetic_field()

        if use_tilt_compensation:
            # Get accelerometer data for tilt compensation
            accel_x, accel_y, accel_z = self.get_acceleration()

            # Calculate roll and pitch
            roll = math.atan2(accel_y, accel_z)
            pitch = math.atan2(-accel_x, math.sqrt(accel_y**2 + accel_z**2))

            # Tilt compensated magnetic field
            mag_x_comp = mag_x * math.cos(pitch) + mag_z * math.sin(pitch)
            mag_y_comp = (mag_x * math.sin(roll) * math.sin(pitch) +
                         mag_y * math.cos(roll) -
                         mag_z * math.sin(roll) * math.cos(pitch))

            heading = math.atan2(mag_y_comp, mag_x_comp)
        else:
            # Simple heading calculation (sensor must be level)
            heading = math.atan2(mag_y, mag_x)

        # Convert to degrees
        heading_degrees = math.degrees(heading)

        # Normalize to 0-360
        if heading_degrees < 0:
            heading_degrees += 360

        # Track for stability detection
        self.previous_readings.append(heading_degrees)
        if len(self.previous_readings) > self.stability_window:
            self.previous_readings.pop(0)

        return heading_degrees

    def get_cardinal_direction(self, use_16_directions=False):
        """
        Get cardinal direction from current heading.

        Args:
            use_16_directions (bool): Use 16-point compass if True, 8-point if False

        Returns:
            str: Cardinal direction (e.g., "N", "NE", "E", "SE", etc.)
        """
        heading = self.get_heading()

        if use_16_directions:
            # 16-point compass rose
            directions = [
                "N", "NNE", "NE", "ENE",
                "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW",
                "W", "WNW", "NW", "NNW"
            ]
            index = int((heading + 11.25) / 22.5) % 16
        else:
            # 8-point compass rose
            directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            index = int((heading + 22.5) / 45) % 8

        return directions[index]

    def get_heading_difference(self, target_heading):
        """
        Calculate the shortest angular difference between current heading and target.
        Useful for navigation - tells you how many degrees to turn.

        Args:
            target_heading (float): Target heading in degrees (0-360)

        Returns:
            float: Difference in degrees (-180 to 180)
                  Negative = turn left, Positive = turn right
        """
        current = self.get_heading()
        diff = target_heading - current

        # Normalize to -180 to 180
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        return diff

    def is_heading_stable(self, threshold=5.0):
        """
        Check if compass heading is stable (not fluctuating).

        Args:
            threshold (float): Maximum acceptable variation in degrees

        Returns:
            bool: True if heading is stable, False if fluctuating
        """
        if len(self.previous_readings) < self.stability_window:
            return False

        # Calculate standard deviation of recent readings
        mean = sum(self.previous_readings) / len(self.previous_readings)
        variance = sum((x - mean) ** 2 for x in self.previous_readings) / len(self.previous_readings)
        std_dev = math.sqrt(variance)

        return std_dev < threshold

    def get_all_data(self):
        """
        Get all compass and sensor data in one call.

        Returns:
            dict: Dictionary containing all sensor readings
        """
        mag_x, mag_y, mag_z = self.get_magnetic_field()
        accel_x, accel_y, accel_z = self.get_acceleration()
        heading = self.get_heading()

        return {
            'heading': heading,
            'direction': self.get_cardinal_direction(),
            'mag_x': mag_x,
            'mag_y': mag_y,
            'mag_z': mag_z,
            'accel_x': accel_x,
            'accel_y': accel_y,
            'accel_z': accel_z,
            'is_stable': self.is_heading_stable()
        }

    def calibrate(self):
        """
        Perform magnetometer calibration.

        This function guides the user through rotating the sensor to find
        min/max values for each axis, then calculates calibration offsets.

        Usage:
            compass.calibrate()
            # Follow on-screen instructions
        """
        print("\n" + "="*60)
        print("MAGNETOMETER CALIBRATION")
        print("="*60)
        print("\nInstructions:")
        print("1. Slowly rotate the sensor in ALL directions")
        print("2. Make complete circles on all 3 axes")
        print("3. Keep rotating for 30 seconds")
        print("4. Try to cover as many orientations as possible")
        print("\nPress Enter to start calibration...")
        input()

        print("\nCalibrating... (30 seconds)")
        print("Keep rotating the sensor!")

        # Collect min/max values
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        start_time = time.time()
        sample_count = 0

        while time.time() - start_time < 30:
            mag_x, mag_y, mag_z = self.mag.magnetic

            min_x = min(min_x, mag_x)
            max_x = max(max_x, mag_x)
            min_y = min(min_y, mag_y)
            max_y = max(max_y, mag_y)
            min_z = min(min_z, mag_z)
            max_z = max(max_z, mag_z)

            sample_count += 1

            # Progress indicator
            elapsed = int(time.time() - start_time)
            print(f"Time: {elapsed}/30 sec | Samples: {sample_count}", end='\r')

            time.sleep(0.05)

        # Calculate offsets (hard iron correction)
        self.cal_offset_x = (max_x + min_x) / 2
        self.cal_offset_y = (max_y + min_y) / 2
        self.cal_offset_z = (max_z + min_z) / 2

        print("\n\n" + "="*60)
        print("CALIBRATION COMPLETE!")
        print("="*60)
        print(f"\nCalibration offsets:")
        print(f"  X: {self.cal_offset_x:.2f} µT")
        print(f"  Y: {self.cal_offset_y:.2f} µT")
        print(f"  Z: {self.cal_offset_z:.2f} µT")
        print(f"\nSamples collected: {sample_count}")
        print("\nTo use these offsets in your code:")
        print(f"compass = CompassManager(calibration_offset=({self.cal_offset_x:.2f}, {self.cal_offset_y:.2f}, {self.cal_offset_z:.2f}))")
        print("\n" + "="*60)

    def get_visual_compass(self, width=40):
        """
        Get a text-based visual representation of the compass.

        Args:
            width (int): Width of the compass display

        Returns:
            str: ASCII art compass display
        """
        heading = self.get_heading()
        direction = self.get_cardinal_direction()

        # Create compass arrow
        arrow_pos = int((heading / 360) * width)
        compass_line = ['-'] * width
        compass_line[arrow_pos] = '^'

        # Direction labels
        labels = "N    E    S    W    N"
        label_line = labels.center(width)

        compass_str = f"""
┌{'─' * width}┐
│{''.join(compass_line)}│
│{label_line}│
└{'─' * width}┘
  Heading: {heading:6.1f}° ({direction})
"""
        return compass_str


# Example usage and testing
if __name__ == "__main__":
    """
    Test script to verify compass functionality.
    Run this to make sure your compass is working correctly.
    """
    print("="*60)
    print("Adafruit 10-DOF IMU Compass Test")
    print("="*60)

    try:
        # Initialize compass
        compass = CompassManager()
        print()

        # Menu
        print("Select test mode:")
        print("1. Live compass display")
        print("2. Calibrate magnetometer")
        print("3. View all sensor data")
        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "2":
            # Calibration mode
            compass.calibrate()
            print("\nRestarting with calibrated values...")
            time.sleep(2)

        # Live display
        print("\n" + "="*60)
        print("Live Compass Display (Ctrl+C to exit)")
        print("="*60)
        print("Keep sensor level for accurate readings\n")

        while True:
            if choice == "3":
                # Detailed data view
                data = compass.get_all_data()
                print("\n" + "-"*60)
                print(f"Heading:    {data['heading']:6.1f}° ({data['direction']})")
                print(f"Magnetic:   X={data['mag_x']:7.2f} Y={data['mag_y']:7.2f} Z={data['mag_z']:7.2f} µT")
                print(f"Accel:      X={data['accel_x']:7.2f} Y={data['accel_y']:7.2f} Z={data['accel_z']:7.2f} m/s²")
                print(f"Stable:     {'Yes' if data['is_stable'] else 'No'}")
                time.sleep(0.5)
            else:
                # Visual compass display
                heading = compass.get_heading()
                direction = compass.get_cardinal_direction()
                mag_x, mag_y, mag_z = compass.get_magnetic_field()
                stable = "✓" if compass.is_heading_stable() else "✗"

                print(f"Heading: {heading:6.1f}° ({direction:3s}) | " +
                      f"Mag: X={mag_x:6.1f} Y={mag_y:6.1f} Z={mag_z:6.1f} µT | " +
                      f"Stable: {stable}", end='\r')
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Test complete!")
        print("="*60)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check wiring connections")
        print("2. Verify I2C is enabled: sudo raspi-config")
        print("3. Check I2C devices: sudo i2cdetect -y 1")
        print("   Should see: 0x19 (accel) and 0x1e (mag)")
        print("4. Install libraries: sudo pip3 install adafruit-circuitpython-lsm303dlh-mag adafruit-circuitpython-lsm303-accel")
        print()
        print("="*60)