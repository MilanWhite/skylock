# MH-FMD Buzzer Module Setup Guide

## Overview
This guide will help you set up the MH-FMD buzzer module with your Raspberry Pi for audio alerts and notifications.

## Hardware Requirements
- Raspberry Pi (any model with GPIO)
- MH-FMD Buzzer Module (active or passive)
- Jumper wires (3x female-to-female or male-to-female)

---

## Buzzer Types

### Active Buzzer
- Has internal oscillator
- Just needs power to make sound
- **Simpler** - just on/off control
- Makes a fixed tone/beep

### Passive Buzzer
- Requires PWM signal
- **More flexible** - can play different tones/melodies
- Can create musical notes

**How to tell the difference:**
- Active buzzers usually have a sticker/seal on top
- Passive buzzers have an exposed circuit board on top
- If unsure, connect it: active will beep with just power, passive won't

---

## Hardware Setup

### Wiring Connections

| Buzzer Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| VCC or +   | Pin 1 (3.3V) or Pin 2 (5V) | Power |
| GND or -   | Pin 6 (GND)      | Ground |
| I/O or S   | Pin 11 (GPIO 17) | Signal/Control |

**Note:** You can use any available GPIO pin for the signal. GPIO 17 (Pin 11) is just the default.

### Wiring Diagram
```
Raspberry Pi          MH-FMD Buzzer
  Pin 2 (5V)   -----> VCC (+)
  Pin 11 (GPIO 17) -> I/O (S)
  Pin 6 (GND)  -----> GND (-)
```

**Power Options:**
- Most MH-FMD modules work with both 3.3V and 5V
- 5V gives louder sound
- Use 3.3V if 5V is too loud or already in use

---

## Software Setup

### Step 1: Install RPi.GPIO (Usually Pre-installed)
```bash
sudo apt-get update
sudo apt-get install python3-rpi.gpio
```

### Step 2: Verify Installation
```bash
python3 -c "import RPi.GPIO; print('GPIO library installed')"
```

### Step 3: No Additional Configuration Needed!
GPIO pins don't need special setup like I2C. Just wire and code!

---

## Using the Buzzer Module

### Basic Usage
```python
from buzzer_module import BuzzerManager

# Initialize buzzer on GPIO 17 (active buzzer)
buzzer = BuzzerManager(pin=17, buzzer_type='active')

# Simple beep
buzzer.beep()

# Multiple beeps
buzzer.beep(times=3, duration=0.2, pause=0.1)

# Cleanup when done
buzzer.cleanup()
```

### For Passive Buzzer
```python
# Initialize as passive
buzzer = BuzzerManager(pin=17, buzzer_type='passive')

# Play a tone (440 Hz = A note)
buzzer.play_tone(440, duration=0.5)

# Play by note name
buzzer.play_tone('A4', duration=0.5)

# Play a melody
notes = ['C4', 'E4', 'G4', 'C5']
durations = [0.3, 0.3, 0.3, 0.5]
buzzer.play_melody(notes, durations)

buzzer.cleanup()
```

---

## Available Methods

### Basic Control

| Method | Description | Example |
|--------|-------------|---------|
| `on()` | Turn buzzer on continuously | `buzzer.on()` |
| `off()` | Turn buzzer off | `buzzer.off()` |
| `beep(duration, times, pause)` | Make beep(s) | `buzzer.beep(0.2, times=3)` |
| `beep_pattern(pattern)` | Play beep pattern | `buzzer.beep_pattern([0.1, 0.1, 0.3])` |
| `cleanup()` | Clean up GPIO | `buzzer.cleanup()` |

### Passive Buzzer Only

| Method | Description | Example |
|--------|-------------|---------|
| `play_tone(freq, duration)` | Play specific tone | `buzzer.play_tone(440, 0.5)` |
| `play_melody(notes, durations)` | Play melody | `buzzer.play_melody(['C4', 'E4'], [0.3, 0.3])` |

### Pre-defined Sounds

| Method | Description | Use Case |
|--------|-------------|----------|
| `success_sound()` | Success notification | Operation completed |
| `error_sound()` | Error notification | Something failed |
| `warning_sound()` | Warning notification | Attention needed |
| `startup_sound()` | Startup melody | System boot |
| `sos_pattern()` | SOS distress signal | Emergency |
| `alarm_sound(duration)` | Alarm sound | Alert/alarm |
| `notification_sound(level)` | Generic notification | Info/success/warning/error |

---

## Usage Examples

### Example 1: Simple Notification System
```python
from buzzer_module import BuzzerManager

buzzer = BuzzerManager(pin=17)

def notify(event_type):
    """Send audio notification based on event."""
    if event_type == 'success':
        buzzer.success_sound()
    elif event_type == 'error':
        buzzer.error_sound()
    elif event_type == 'warning':
        buzzer.warning_sound()

# Use it
notify('success')  # Beep beep!
notify('error')    # Long beep
```

### Example 2: Compass Direction Alerts
```python
from buzzer_module import BuzzerManager
from compass_module import CompassManager

buzzer = BuzzerManager(pin=17)
compass = CompassManager()

target_heading = 0  # North

while True:
    current = compass.get_heading()
    diff = compass.get_heading_difference(target_heading)

    if abs(diff) < 5:
        # On target!
        buzzer.success_sound()
        break
    elif abs(diff) < 15:
        # Close to target
        buzzer.beep(0.1)

    time.sleep(1)

buzzer.cleanup()
```

### Example 3: Timed Alerts
```python
from buzzer_module import BuzzerManager
from rtc_module import RTCManager
import time

buzzer = BuzzerManager(pin=17)
rtc = RTCManager()

# Beep every minute
print("Beeping every minute (Ctrl+C to stop)")

try:
    last_minute = None
    while True:
        _, _, _, _, minute, _ = rtc.get_datetime_components()

        if minute != last_minute:
            buzzer.beep()
            print(f"Beep! {rtc.get_time_string()}")
            last_minute = minute

        time.sleep(1)

except KeyboardInterrupt:
    buzzer.cleanup()
```

### Example 4: Button Press Feedback
```python
from buzzer_module import BuzzerManager
import RPi.GPIO as GPIO
import time

# Setup
BUZZER_PIN = 17
BUTTON_PIN = 27

buzzer = BuzzerManager(pin=BUZZER_PIN)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Press button for beep (Ctrl+C to exit)")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            buzzer.beep(0.1)
            time.sleep(0.3)  # Debounce

        time.sleep(0.01)

except KeyboardInterrupt:
    buzzer.cleanup()
    GPIO.cleanup()
```

### Example 5: Play Melody (Passive Buzzer)
```python
from buzzer_module import BuzzerManager

buzzer = BuzzerManager(pin=17, buzzer_type='passive')

# Twinkle Twinkle Little Star
notes = [
    'C4', 'C4', 'G4', 'G4', 'A4', 'A4', 'G4',
    'F4', 'F4', 'E4', 'E4', 'D4', 'D4', 'C4'
]

durations = [
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.6,
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.6
]

print("Playing melody...")
buzzer.play_melody(notes, durations)

buzzer.cleanup()
```

---

## Musical Notes Reference (Passive Buzzer)

Available note names for `play_tone()` and `play_melody()`:

| Octave 4 | Frequency | Octave 5 | Frequency |
|----------|-----------|----------|-----------|
| C4 | 261 Hz | C5 | 523 Hz |
| D4 | 294 Hz | D5 | 587 Hz |
| E4 | 329 Hz | E5 | 659 Hz |
| F4 | 349 Hz | F5 | 698 Hz |
| G4 | 392 Hz | G5 | 784 Hz |
| A4 | 440 Hz | A5 | 880 Hz |
| B4 | 494 Hz | B5 | 988 Hz |

**REST** = 0 Hz (silence)

You can also use raw frequencies in Hz:
```python
buzzer.play_tone(440, 0.5)  # A4 note
```

---

## Testing

Run the test script:
```bash
python3 buzzer_module.py
```

This will:
1. Ask for buzzer type (active/passive)
2. Ask for GPIO pin number
3. Let you test various sounds

---

## Troubleshooting

### Problem: No sound at all
**Solution:**
- Check wiring connections (especially ground)
- Verify correct GPIO pin in code
- Try different power pin (3.3V vs 5V)
- Test with simple on/off:
  ```python
  buzzer.on()
  time.sleep(1)
  buzzer.off()
  ```

### Problem: Very quiet/weak sound
**Solution:**
- Use 5V instead of 3.3V for power
- Check if buzzer is damaged
- For passive buzzer, try different duty cycles

### Problem: Buzzer stays on after program exits
**Solution:**
- Always call `buzzer.cleanup()` at end
- Use try/finally blocks:
  ```python
  buzzer = BuzzerManager(pin=17)
  try:
      buzzer.beep()
  finally:
      buzzer.cleanup()
  ```

### Problem: "RuntimeWarning: This channel is already in use"
**Solution:**
- GPIO pin conflict with another program
- Clean up before running again:
  ```bash
  python3 -c "import RPi.GPIO as GPIO; GPIO.cleanup()"
  ```
- Use different GPIO pin

### Problem: Passive buzzer sounds like active (no tones)
**Solution:**
- Your buzzer might actually be active
- Try initializing as active instead:
  ```python
  buzzer = BuzzerManager(pin=17, buzzer_type='active')
  ```

### Problem: "ImportError: No module named RPi.GPIO"
**Solution:**
```bash
sudo apt-get update
sudo apt-get install python3-rpi.gpio
```

---

## GPIO Pin Options

You can use any available GPIO pin. Common choices:

| GPIO Number | Physical Pin | Notes |
|-------------|--------------|-------|
| GPIO 17 | Pin 11 | Default in examples |
| GPIO 27 | Pin 13 | Good alternative |
| GPIO 22 | Pin 15 | Another option |
| GPIO 23 | Pin 16 | Also available |

**Avoid these pins:**
- GPIO 2, 3 (I2C - used by RTC and compass)
- GPIO 14, 15 (UART)
- GPIO 9, 10, 11 (SPI - if using SPI display)

---

## Integration with Other Modules

### With RTC
```python
from buzzer_module import BuzzerManager
from rtc_module import RTCManager

buzzer = BuzzerManager(pin=17)
rtc = RTCManager()

# Beep with timestamp
print(f"{rtc.get_timestamp()} System ready")
buzzer.startup_sound()
```

### With Compass
```python
from buzzer_module import BuzzerManager
from compass_module import CompassManager

buzzer = BuzzerManager(pin=17)
compass = CompassManager()

# Alert when facing North
if compass.get_cardinal_direction() == 'N':
    buzzer.success_sound()
```

### All Three Together
```python
from buzzer_module import BuzzerManager
from compass_module import CompassManager
from rtc_module import RTCManager

buzzer = BuzzerManager(pin=17)
compass = CompassManager()
rtc = RTCManager()

# Log heading changes with audio feedback
heading = compass.get_heading()
timestamp = rtc.get_timestamp()
print(f"{timestamp} Heading: {heading:.1f}°")
buzzer.beep(0.1)
```

---

## Important Notes

### Power Consumption
- Active buzzer: ~30mA
- Passive buzzer: ~10-20mA
- Safe to power from GPIO pins

### Sound Volume
- 5V = Louder
- 3.3V = Quieter
- Can't control volume in software (use PWM duty cycle for passive if needed)

### Cleanup
**Always cleanup GPIO when done:**
```python
buzzer.cleanup()
```

Or use context managers:
```python
buzzer = BuzzerManager(pin=17)
try:
    buzzer.beep()
finally:
    buzzer.cleanup()
```

---

## Project Integration Checklist

- [ ] Hardware connected to correct GPIO pin
- [ ] Power and ground connected
- [ ] Tested with `python3 buzzer_module.py`
- [ ] Determined if active or passive buzzer
- [ ] Added to main project code
- [ ] Cleanup called at program end

---
