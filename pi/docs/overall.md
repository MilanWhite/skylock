# Raspberry Pi Navigation System - Complete Project Overview

## 📦 Project Components

This project integrates three hardware modules with your Raspberry Pi:

1. **DS3231 RTC Module** - Real-time clock for accurate timekeeping
2. **Adafruit 10-DOF IMU** - Compass/magnetometer for navigation
3. **MH-FMD Buzzer Module** - Audio alerts and feedback

---

## 📁 Project Structure

```
your-project/
├── rtc_module.py           # RTC functionality
├── compass_module.py       # Compass/magnetometer functionality
├── buzzer_module.py        # Buzzer/audio functionality
├── combined_example.py     # Complete integration example
├── quick_test.py          # Quick test all modules
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── docs/                  # Individual module documentation
    ├── rtc_README.md
    ├── compass_README.md
    └── buzzer_README.md
```

---

## 🔌 Complete Wiring Diagram

### All Modules Connected

```
Raspberry Pi GPIO                    Modules
─────────────────────────────────────────────────────────
Pin 1  (3.3V)  ─┬─────────────────> RTC VCC (or use 5V)
                └─────────────────> 10-DOF VCC (or use 5V)

Pin 2  (5V)    ──────────────────> Buzzer VCC

Pin 3  (SDA)   ─┬─────────────────> RTC SDA
                └─────────────────> 10-DOF SDA  (shared I2C)

Pin 5  (SCL)   ─┬─────────────────> RTC SCL
                └─────────────────> 10-DOF SCL  (shared I2C)

Pin 6  (GND)   ─┬─────────────────> RTC GND
                ├─────────────────> 10-DOF GND
                └─────────────────> Buzzer GND  (all grounds connected)

Pin 11 (GPIO17)──────────────────> Buzzer I/O
```

### I2C Address Map
- `0x19` - LSM303 Accelerometer
- `0x1e` - LSM303 Magnetometer
- `0x68` - DS3231 RTC (shows as UU after driver loaded)
- `0x6b` - L3GD20 Gyroscope
- `0x77` - BMP280 Barometer

---

## 🚀 Quick Start Guide

### Step 1: Hardware Setup (One Time)
```bash
# 1. Connect all modules following the wiring diagram above

# 2. Enable I2C
sudo raspi-config
# Interface Options → I2C → Enable → Reboot

# 3. Verify connections
sudo i2cdetect -y 1
# Should see: 0x19, 0x1e, 0x68, 0x6b, 0x77
```

### Step 2: Software Setup (One Time)
```bash
# 1. Clone/copy project files to Pi

# 2. Install dependencies
sudo pip3 install -r requirements.txt

# 3. Configure RTC
sudo nano /boot/config.txt  # or /boot/firmware/config.txt
# Add: dtoverlay=i2c-rtc,ds3231
# Save and reboot

# 4. Set RTC time (after reboot)
sudo ntpdate -s time.nist.gov  # If you have internet
sudo hwclock -w                 # Write to RTC

# 5. Calibrate compass (IMPORTANT!)
python3 compass_module.py
# Select option 2, follow instructions
# Save the calibration offsets it gives you
```

### Step 3: Test Everything
```bash
# Quick test all modules
python3 quick_test.py

# Test individual modules
python3 rtc_module.py
python3 compass_module.py
python3 buzzer_module.py

# Try the full integration example
python3 combined_example.py
```

---

## 💻 Basic Usage Examples

### Example 1: Simple Status Display
```python
from rtc_module import RTCManager
from compass_module import CompassManager
from buzzer_module import BuzzerManager

# Initialize
rtc = RTCManager()
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))
buzzer = BuzzerManager(pin=17)

# Get status
time = rtc.get_datetime_string()
heading = compass.get_heading()
direction = compass.get_cardinal_direction()

# Display and alert
print(f"[{time}] Heading: {heading:.1f}° ({direction})")
buzzer.beep()

# Cleanup
buzzer.cleanup()
```

### Example 2: Navigation Assistant
```python
from rtc_module import RTCManager
from compass_module import CompassManager
from buzzer_module import BuzzerManager
import time

rtc = RTCManager()
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))
buzzer = BuzzerManager(pin=17)

target = 0  # Navigate to North

print(f"Navigate to North (0°)")
buzzer.startup_sound()

try:
    while True:
        current = compass.get_heading()
        diff = compass.get_heading_difference(target)
        time_str = rtc.get_time_string()

        if abs(diff) < 5:
            print(f"[{time_str}] ON TARGET! {current:.1f}°")
            buzzer.success_sound()
            break
        else:
            turn = "LEFT" if diff < 0 else "RIGHT"
            print(f"[{time_str}] Turn {turn} {abs(diff):.1f}°")
            buzzer.beep(0.05)

        time.sleep(1)
finally:
    buzzer.cleanup()
```

### Example 3: Data Logger
```python
from rtc_module import RTCManager
from compass_module import CompassManager
from buzzer_module import BuzzerManager
import time

rtc = RTCManager()
compass = CompassManager(calibration_offset=(12.34, -5.67, 8.90))
buzzer = BuzzerManager(pin=17)

filename = f"nav_log_{rtc.get_date_string()}.txt"
buzzer.beep(0.1, times=2)

try:
    with open(filename, 'a') as f:
        f.write(f"\nLog started: {rtc.get_datetime_string()}\n")
        f.write("Time                | Heading | Direction\n")
        f.write("-" * 50 + "\n")

        count = 0
        while True:
            timestamp = rtc.get_datetime_string()
            heading = compass.get_heading()
            direction = compass.get_cardinal_direction()

            line = f"{timestamp} | {heading:6.1f}° | {direction}\n"
            f.write(line)
            f.flush()

            count += 1
            if count % 10 == 0:
                buzzer.beep(0.05)

            print(f"Logged {count} entries", end='\r')
            time.sleep(2)

except KeyboardInterrupt:
    print(f"\nSaved {count} entries to {filename}")
    buzzer.success_sound()
finally:
    buzzer.cleanup()
```

---

## 📚 Module Reference

### RTC Module (`rtc_module.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `get_datetime_string()` | str | "2025-11-07 18:30:45" |
| `get_time_string()` | str | "18:30:45" |
| `get_date_string()` | str | "2025-11-07" |
| `get_timestamp()` | str | "[2025-11-07 18:30:45]" |
| `get_temperature()` | float | Temperature in °C |
| `get_day_of_week()` | str | "Thursday" |

### Compass Module (`compass_module.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `get_heading()` | float | Heading 0-360° |
| `get_cardinal_direction()` | str | "N", "NE", "E", etc. |
| `get_heading_difference(target)` | float | Degrees to turn |
| `is_heading_stable()` | bool | True if stable |
| `get_magnetic_field()` | tuple | (x, y, z) in µT |
| `calibrate()` | - | Run calibration |

### Buzzer Module (`buzzer_module.py`)

| Method | Description |
|--------|-------------|
| `beep(duration, times, pause)` | Make beep(s) |
| `success_sound()` | Success notification |
| `error_sound()` | Error notification |
| `warning_sound()` | Warning notification |
| `sos_pattern()` | SOS emergency signal |
| `play_tone(freq, duration)` | Play tone (passive only) |
| `cleanup()` | Clean up GPIO |

---

## 🛠️ Troubleshooting

### RTC Issues
```bash
# Check if detected
sudo i2cdetect -y 1  # Should see 0x68 or UU

# Check if driver loaded
dmesg | grep rtc

# Read RTC time
sudo hwclock -r

# Write system time to RTC
sudo hwclock -w
```

### Compass Issues
```bash
# Check if detected
sudo i2cdetect -y 1  # Should see 0x19 and 0x1e

# Calibrate (most common fix!)
python3 compass_module.py  # Option 2

# Test readings
python3 compass_module.py  # Option 1
```

### Buzzer Issues
```bash
# Check GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.OUT); GPIO.output(17, 1); import time; time.sleep(1); GPIO.cleanup()"

# Try different pin
# Edit buzzer_module.py or pass different pin number

# Clean up stuck GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.cleanup()"
```

### General Issues
```bash
# Check all I2C devices
sudo i2cdetect -y 1

# Install missing dependencies
sudo pip3 install -r requirements.txt

# Check Python version (needs 3.x)
python3 --version

# Update system
sudo apt-get update
sudo apt-get upgrade
```

---

## 📋 Team Development Workflow

### Initial Setup (One Person)
1. Wire all hardware
2. Install software and libraries
3. Test all modules
4. Calibrate compass
5. Push code to Git repository

### Team Members Join
1. Clone repository
2. SSH into the Raspberry Pi
3. Run `python3 quick_test.py` to verify
4. Start coding!

### Development Tips
- **One Pi, multiple developers**: Everyone SSHs into the same Pi
- **Use Git**: Version control for code collaboration
- **Document calibration values**: Save in README or config file
- **Test frequently**: Run `quick_test.py` after changes

---

## 🎯 Project Ideas

### Navigation Projects
- Digital compass with heading display
- GPS-free navigation system
- Treasure hunt game
- Direction finder
- Magnetic field mapper

### Data Logging
- Environmental monitoring
- Movement tracking
- Orientation logger
- Time-series compass data

### Interactive Applications
- Audio navigation assistant
- Heading-based alerts
- Direction game
- Compass calibration tool

---

## 📞 Support

### Documentation
- Each module has detailed README in `docs/` folder
- Run modules directly for interactive testing
- Check `combined_example.py` for integration patterns

### Common Questions
**Q: Do I need internet?**
A: Only for initial time sync. After that, RTC keeps time offline.

**Q: Can I use different GPIO pins?**
A: Yes! Just change the pin number when initializing modules.

**Q: Why is my compass inaccurate?**
A: You need to calibrate! Run `python3 compass_module.py` (option 2).

**Q: Can I add more sensors?**
A: Yes! The I2C bus supports multiple devices with different addresses.

---

## ✅ Checklist Before Starting Your Project

- [ ] All hardware connected and verified with `i2cdetect`
- [ ] I2C enabled in `raspi-config`
- [ ] RTC driver added to config.txt
- [ ] Python libraries installed from requirements.txt
- [ ] RTC time set correctly
- [ ] Compass calibrated and offsets saved
- [ ] Buzzer tested and working
- [ ] All modules tested with `quick_test.py`
- [ ] Team members can access the Pi
- [ ] Code repository set up (Git)

---
