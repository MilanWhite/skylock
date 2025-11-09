# Adafruit 10-DOF IMU Compass Setup Guide

## Overview
This guide will help you set up the Adafruit 10-DOF IMU breakout for compass/heading functionality with the Raspberry Pi.

## Hardware Requirements
- Raspberry Pi (any model with GPIO)
- Adafruit 10-DOF IMU Breakout Board
  - LSM303DLHC or LSM303AGR (Accelerometer + Magnetometer)
  - L3GD20H or L3GD20 (Gyroscope)
  - BMP180 or BMP280 (Barometer/Temperature)
- Jumper wires (4x female-to-female or male-to-female)

---

## Hardware Setup

### Wiring Connections
Connect the 10-DOF IMU to your Raspberry Pi:

| 10-DOF Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| VIN        | Pin 1 (3.3V) or Pin 2 (5V) | Power |
| GND        | Pin 6 (GND)      | Ground |
| SDA        | Pin 3 (GPIO 2)   | I2C Data |
| SCL        | Pin 5 (GPIO 3)   | I2C Clock |

**Note:** If the MHS display is already connected, use the GPIO pass-through pins on top. You can share the same I2C bus with the RTC module.

### Wiring Diagram
```
Raspberry Pi          10-DOF IMU
  Pin 1 (3.3V) -----> VIN
  Pin 3 (SDA)  -----> SDA (shared with RTC)
  Pin 5 (SCL)  -----> SCL (shared with RTC)
  Pin 6 (GND)  -----> GND
```

**Important:** Both the RTC and IMU can share the same I2C bus (same SDA/SCL pins) since they have different I2C addresses.

---

## Software Setup

### Step 1: Enable I2C
If you haven't already done this for the RTC:
```bash
sudo raspi-config
```
- Navigate to: **Interface Options → I2C → Enable**
- Reboot: `sudo reboot`

### Step 2: Verify I2C Connection
Check if the 10-DOF sensors are detected:
```bash
sudo i2cdetect -y 1
```

You should see these addresses:
- `0x19` - LSM303 Accelerometer
- `0x1e` - LSM303 Magnetometer
- `0x6b` (or `0x6a`) - L3GD20 Gyroscope
- `0x77` - BMP280 Barometer

Example output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- 19 -- -- -- -- 1e --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
...
60: -- -- -- -- -- -- -- -- UU -- -- 6b -- -- -- --
70: -- -- -- -- -- -- -- 77
```

### Step 3: Install Python Libraries
```bash
sudo pip3 install adafruit-circuitpython-lsm303dlh-mag
sudo pip3 install adafruit-circuitpython-lsm303-accel
```

Optional (for full 10-DOF functionality):
```bash
sudo pip3 install adafruit-circuitpython-l3gd20      # Gyroscope
sudo pip3 install adafruit-circuitpython-bmp280      # Barometer
```

---

## Calibration (Important!)

The magnetometer needs calibration for accurate compass readings. Magnetic interference from electronics, metal objects, and the Earth's magnetic field variations require calibration.

### Quick Calibration
Run the calibration routine:
```bash
python3 compass_module.py
# Select option 2 (Calibrate magnetometer)
# Follow on-screen instructions
```

**During calibration:**
1. Rotate the sensor in ALL directions
2. Make complete circles on all 3 axes (like drawing a sphere in the air)
3. Keep rotating for the full 30 seconds
4. The more orientations you cover, the better the calibration

**After calibration**, the script will give you calibration offsets like:
```
Calibration offsets:
  X: 12.34 µT
  Y: -5.67 µT
  Z: 8.90 µT
```

### Using Calibration in Your Code
```python
from compass_module import CompassManager

# Use the calibration offsets from the calibration routine
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

heading = compass.get_heading()
```

**Note:** Save your calibration values! You'll need to recalibrate if:
- You move to a different location
- You add/remove nearby metal objects or electronics
- The sensor orientation changes permanently

---

## Using the Compass Module

### Basic Usage
```python
from compass_module import CompassManager

# Initialize compass (without calibration)
compass = CompassManager()

# Or with calibration offsets
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

# Get compass heading
heading = compass.get_heading()
print(f"Heading: {heading:.1f}°")  # e.g., "Heading: 45.5°"

# Get cardinal direction
direction = compass.get_cardinal_direction()
print(f"Direction: {direction}")  # e.g., "Direction: NE"
```

### Available Methods

| Method | Description | Example Output |
|--------|-------------|----------------|
| `get_heading()` | Get compass heading (0-360°) | `45.5` |
| `get_cardinal_direction()` | Get 8-point compass direction | `"NE"` |
| `get_cardinal_direction(use_16_directions=True)` | Get 16-point direction | `"NNE"` |
| `get_magnetic_field()` | Raw magnetometer data | `(12.3, -5.6, 8.9)` |
| `get_acceleration()` | Accelerometer data | `(0.1, 0.2, 9.8)` |
| `is_heading_stable()` | Check if reading is stable | `True` or `False` |
| `get_heading_difference(target)` | Angle to turn to target | `-45.0` (turn left) |
| `get_all_data()` | All sensor data at once | See below |
| `calibrate()` | Run calibration routine | Interactive |

### Example: Navigation
```python
from compass_module import CompassManager

compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

# Current heading
current = compass.get_heading()
print(f"Current heading: {current:.1f}°")

# Want to go North (0°)
target = 0
diff = compass.get_heading_difference(target)

if abs(diff) < 5:
    print("You're heading in the right direction!")
elif diff < 0:
    print(f"Turn left {abs(diff):.1f}°")
else:
    print(f"Turn right {diff:.1f}°")
```

### Example: Display with Direction
```python
from compass_module import CompassManager
import time

compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

print("Compass Display (Ctrl+C to exit)")
while True:
    heading = compass.get_heading()
    direction = compass.get_cardinal_direction()
    stable = "✓" if compass.is_heading_stable() else "✗"

    print(f"Heading: {heading:6.1f}° ({direction:3s}) | Stable: {stable}", end='\r')
    time.sleep(0.1)
```

### Example: Get All Data
```python
from compass_module import CompassManager

compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

data = compass.get_all_data()

print(f"Heading: {data['heading']:.1f}°")
print(f"Direction: {data['direction']}")
print(f"Magnetic field: X={data['mag_x']:.2f} Y={data['mag_y']:.2f} Z={data['mag_z']:.2f} µT")
print(f"Acceleration: X={data['accel_x']:.2f} Y={data['accel_y']:.2f} Z={data['accel_z']:.2f} m/s²")
print(f"Stable: {data['is_stable']}")
```

---

## Testing

Run the test script to verify everything works:
```bash
python3 compass_module.py
```

**Test modes:**
1. **Live compass display** - Real-time heading updates
2. **Calibrate magnetometer** - Run calibration routine
3. **View all sensor data** - Detailed sensor readings

---

## Important Notes

### Keep Sensor Level
For accurate compass readings:
- ✓ Keep the sensor as level as possible (parallel to ground)
- ✓ If the sensor is tilted, use tilt compensation:
  ```python
  heading = compass.get_heading(use_tilt_compensation=True)
  ```

### Avoid Magnetic Interference
Magnetometers are sensitive to:
- ❌ Nearby electronics (motors, speakers, power supplies)
- ❌ Metal objects (especially ferromagnetic materials)
- ❌ Permanent magnets
- ❌ Strong currents in wires

**Best practices:**
- Keep at least 10cm away from other electronics
- Mount sensor away from motors and power cables
- Calibrate in the location where you'll use it
- Recalibrate if you change the setup

### Heading Stability
The `is_heading_stable()` method helps detect when readings are reliable:
```python
if compass.is_heading_stable():
    heading = compass.get_heading()
    # Use this reading - it's stable
else:
    # Keep waiting for stable reading
    pass
```

### Cardinal Directions Reference
- **N** (North): 0° or 360°
- **E** (East): 90°
- **S** (South): 180°
- **W** (West): 270°

**8-point compass:** N, NE, E, SE, S, SW, W, NW
**16-point compass:** N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW

---

## Troubleshooting

### Problem: No sensors detected on I2C
**Solution:**
- Check wiring connections (especially SDA and SCL)
- Verify I2C is enabled: `sudo raspi-config`
- Check devices: `sudo i2cdetect -y 1`
- Try using 3.3V instead of 5V (or vice versa)

### Problem: Heading jumps around wildly
**Solution:**
- **Calibrate the magnetometer!** (most common cause)
- Move away from magnetic interference
- Keep sensor level
- Check for loose wiring

### Problem: Heading is consistently wrong (off by same amount)
**Solution:**
- Need calibration
- Check for nearby magnetic interference
- Verify sensor orientation

### Problem: ImportError for libraries
**Solution:**
```bash
sudo pip3 install --upgrade adafruit-circuitpython-lsm303dlh-mag
sudo pip3 install --upgrade adafruit-circuitpython-lsm303-accel
```

### Problem: Readings are slow or laggy
**Solution:**
- Reduce `time.sleep()` in your loop
- The LSM303 can read at up to 100Hz
- Use `get_all_data()` for efficiency (one I2C transaction)

---

## Combining with RTC

Since both modules share the I2C bus:

```python
from rtc_module import RTCManager
from compass_module import CompassManager

# Initialize both
rtc = RTCManager()
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

# Use together
timestamp = rtc.get_timestamp()
heading = compass.get_heading()
direction = compass.get_cardinal_direction()

print(f"{timestamp} Heading: {heading:.1f}° ({direction})")
# Output: [2025-11-07 18:30:45] Heading: 45.5° (NE)
```

---

## Project Integration Checklist

- [ ] Hardware connected and verified with `i2cdetect`
- [ ] I2C enabled in raspi-config
- [ ] Python libraries installed
- [ ] Magnetometer calibrated
- [ ] Calibration offsets saved in code
- [ ] Test script runs successfully
- [ ] `compass_module.py` imported in main project

---

## Advanced: Tilt Compensation

If your sensor won't always be level, use tilt compensation:

```python
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))

# Get heading with tilt compensation
heading = compass.get_heading(use_tilt_compensation=True)
```

This uses the accelerometer to compensate for tilt, giving accurate headings even when the sensor is not perfectly level.

---
