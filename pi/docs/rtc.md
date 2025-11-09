# DS3231 RTC Module Setup Guide

## Overview
This guide will help you set up and use the DS3231 Real-Time Clock (RTC) module with the Raspberry Pi for our project.

## Hardware Requirements
- Raspberry Pi (any model with GPIO)
- DS3231 RTC Module
- Jumper wires (4x female-to-female or male-to-female)
- CR2032 battery (for the RTC module, to keep time when powered off)

---

## Hardware Setup

### Wiring Connections
Connect the DS3231 to your Raspberry Pi as follows:

| DS3231 Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| VCC        | Pin 1 (3.3V) or Pin 2 (5V) | Power |
| GND        | Pin 6 (GND)      | Ground |
| SDA        | Pin 3 (GPIO 2)   | I2C Data |
| SCL        | Pin 5 (GPIO 3)   | I2C Clock |

**Note:** If the MHS display is already connected, use the GPIO pass-through pins on top of the display.

### Wiring Diagram
```
Raspberry Pi          DS3231 RTC
  Pin 1 (3.3V) -----> VCC
  Pin 3 (SDA)  -----> SDA
  Pin 5 (SCL)  -----> SCL
  Pin 6 (GND)  -----> GND
```

---

## Software Setup

### Step 1: Enable I2C
```bash
sudo raspi-config
```
- Navigate to: **Interface Options → I2C → Enable**
- Reboot when prompted, or manually: `sudo reboot`

### Step 2: Verify I2C Connection
After rebooting, check if the DS3231 is detected:
```bash
sudo i2cdetect -y 1
```

You should see `68` in the output grid (DS3231 I2C address):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
```

### Step 3: Load DS3231 Driver
Edit the boot configuration file:
```bash
# For older Raspberry Pi OS:
sudo nano /boot/config.txt

# For newer Raspberry Pi OS (Bookworm):
sudo nano /boot/firmware/config.txt
```

Add this line at the end:
```
dtoverlay=i2c-rtc,ds3231
```

Save (Ctrl+X, Y, Enter) and reboot:
```bash
sudo reboot
```

### Step 4: Verify Driver Loaded
After reboot, run:
```bash
sudo i2cdetect -y 1
```

Now you should see **UU** instead of 68 (means kernel is using it):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
60: -- -- -- -- -- -- -- -- UU -- -- -- -- -- -- --
```

### Step 5: Remove Fake Hardware Clock (Optional but Recommended)
```bash
sudo apt-get -y remove fake-hwclock
sudo update-rc.d -f fake-hwclock remove
sudo systemctl disable fake-hwclock
```

### Step 6: Install Python Library
```bash
sudo pip3 install adafruit-circuitpython-ds3231
```

---

## Setting the Time

### Option A: With Internet Connection (Recommended)
```bash
# Get current time from internet
sudo ntpdate -s time.nist.gov

# Write system time to RTC
sudo hwclock -w

# Verify it's set correctly
sudo hwclock -r
```

### Option B: Without Internet (Manual Set)
```bash
# Set system time manually (adjust to current time)
sudo date -s "2025-11-07 18:30:00"

# Write to RTC
sudo hwclock -w

# Verify
sudo hwclock -r
```

### Option C: Using Python Script
You can also set the time using the `rtc_module.py`:
```python
from rtc_module import RTCManager

rtc = RTCManager()
rtc.set_datetime(2025, 11, 7, 18, 30, 0)  # year, month, day, hour, minute, second
```

---

## Auto-Load Time on Boot

Make the Pi read time from RTC on every boot:
```bash
sudo nano /etc/rc.local
```

Add this line **before** `exit 0`:
```bash
hwclock -s
```

Save and exit.

---

## Using the RTC Module in Code

### Quick Start
```python
from rtc_module import RTCManager

# Initialize
rtc = RTCManager()

# Get current time
print(rtc.get_datetime_string())  # "2025-11-07 18:30:45"
print(rtc.get_time_string())      # "18:30:45"
print(rtc.get_date_string())      # "2025-11-07"

# Get temperature
temp = rtc.get_temperature()
print(f"Temperature: {temp:.1f}°C")
```

### Available Methods

| Method | Description | Example Output |
|--------|-------------|----------------|
| `get_datetime_string()` | Full date and time | `"2025-11-07 18:30:45"` |
| `get_time_string()` | Time only | `"18:30:45"` |
| `get_date_string()` | Date only | `"2025-11-07"` |
| `get_timestamp()` | Formatted for logging | `"[2025-11-07 18:30:45]"` |
| `get_datetime_components()` | Individual values | `(2025, 11, 7, 18, 30, 45)` |
| `get_temperature()` | RTC chip temperature | `23.5` |
| `get_day_of_week()` | Day name | `"Thursday"` |
| `is_daytime()` | Check if daytime | `True` or `False` |
| `get_formatted_display()` | Multi-line display | See example below |

### Example: Logging with Timestamps
```python
from rtc_module import RTCManager

rtc = RTCManager()

# Log sensor readings
compass_heading = 45.2
log_entry = f"{rtc.get_timestamp()} Compass heading: {compass_heading}°"
print(log_entry)
# Output: [2025-11-07 18:30:45] Compass heading: 45.2°
```

### Example: Display on Screen
```python
from rtc_module import RTCManager

rtc = RTCManager()

# Get formatted display
display_text = rtc.get_formatted_display()
print(display_text)
# Output:
# Thursday, 07/11/2025
# 18:30:45
# Temperature: 23.5°C
```

---

## Testing

Run the test script to verify everything works:
```bash
python3 rtc_module.py
```

This will:
1. Initialize the RTC
2. Display current time in various formats
3. Show a live clock with temperature
4. Help identify any issues

---

## Troubleshooting

### Problem: "Remote I/O error" or module not found
**Solution:**
- Check wiring connections
- Verify I2C is enabled: `sudo raspi-config`
- Check I2C devices detected: `sudo i2cdetect -y 1`
- Make sure driver is added to config.txt

### Problem: Time is wrong after reboot
**Solution:**
- Check if battery is installed in the DS3231 module
- Verify `dtoverlay=i2c-rtc,ds3231` is in config.txt
- Check if `hwclock -s` is in `/etc/rc.local`
- Try setting the time again: `sudo hwclock -w`

### Problem: ImportError for adafruit libraries
**Solution:**
```bash
sudo pip3 install --upgrade adafruit-circuitpython-ds3231
```

### Problem: Permission denied errors
**Solution:**
- Make sure to use `sudo` for hardware clock commands
- Add your user to i2c group: `sudo usermod -a -G i2c $USER`
- Log out and back in

---

## Important Notes

### Battery Life
- The CR2032 battery keeps the RTC running when powered off
- Battery typically lasts 5-8 years
- You'll know it's dead when time resets after power loss
- The RTC works fine without a battery, but won't keep time when powered off

### Time Accuracy
- DS3231 is very accurate: ±2 ppm (about ±1 minute per year)
- Has temperature compensation for better accuracy
- For projects not requiring internet, set time once and forget it

### Working Without Internet
Once time is set, the RTC will maintain accurate time indefinitely (until battery dies):
- ✓ No need to sync with internet
- ✓ Perfect for offline/remote deployments
- ✓ Time persists through power cycles

---

## Project Integration Checklist

- [ ] Hardware connected and verified with `i2cdetect`
- [ ] I2C enabled in raspi-config
- [ ] Driver loaded in config.txt
- [ ] Python library installed
- [ ] Time set correctly
- [ ] Auto-load configured in rc.local
- [ ] Test script runs successfully
- [ ] `rtc_module.py` imported in main project code

---

## Questions?

If you run into issues:
1. Check the troubleshooting section above
2. Run the test script: `python3 rtc_module.py`
3. Verify hardware with: `sudo i2cdetect -y 1`
4. Check system logs: `dmesg | grep rtc`

---
