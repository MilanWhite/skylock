import os
# Fix SDL dynamic linking error - MUST BE BEFORE PYGAME IMPORT
os.environ['SDL_VIDEODRIVER'] = 'x11'
os.environ['SDL_AUDIODRIVER'] = 'alsa'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import json, time, requests, math
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to Python path so we can import from 'server'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pygame
pygame.init()

# Import satellite service
from server.model.repository import SqliteTleRepository
from server.service.satellite_service import Sgp4SatelliteService
from server.service.tle_scheduler_service import TleSchedulerService

from compass_module import CompassManager

# Initialize compass
compass = CompassManager()

API_BASE = "http://192.168.137.1:4000"
DEVICE_ID = "autosat-01"

# User location (these would be updated from GPS in real implementation)
user_lat = 43.7315
user_lon = -79.7624
user_alt = 175.0  # altitude in meters
user_pdop = 2.9

# Satellite tracking
satellite_info = None
last_satellite_update = 0
SATELLITE_UPDATE_INTERVAL = 3  # Update every 3 seconds

# Initialize satellite service with scheduler
try:
    repo = SqliteTleRepository()
    scheduler = TleSchedulerService(repo, tle_group="amateur", interval_seconds=3600)
    satellite_service = Sgp4SatelliteService(repo)
    
    # Start scheduler with initial fetch
    print("Starting scheduler and fetching initial TLE data...")
    scheduler.start(initial_fetch=True)
    
    # Give scheduler a moment to fetch data
    time.sleep(2)
    print("Satellite service initialized successfully")
except Exception as e:
    print(f"Failed to initialize satellite service: {e}")
    satellite_service = None
    scheduler = None

# ====== UI PRIMITIVES ======
W, H = pygame.display.Info().current_w, pygame.display.Info().current_h
screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
FONT = pygame.font.SysFont(None, 40)
FONT_BIG = pygame.font.SysFont(None, 60)
FONT_MED = pygame.font.SysFont(None, 48)
FONT_SMALL = pygame.font.SysFont(None, 28)
BG = (8,10,14)
FG = (220,230,255)
ACCENT = (70,130,255)
OK = (60,180,120)
ERR = (220,80,80)
WARN = (255,180,60)

class Button:
    def __init__(self, rect, label, color):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=14)
        txt = FONT_MED.render(self.label, True, (0,0,0))
        surf.blit(txt, txt.get_rect(center=self.rect.center))
    def hit(self, pos):
        return self.rect.collidepoint(pos)

def draw_text_center(text, y, color=FG, font=FONT_BIG):
    txt = font.render(text, True, color)
    screen.blit(txt, txt.get_rect(center=(W//2, y)))

def draw_location_info(surf, x, y):
    """Draw current location information"""
    info_lines = [
        f"Lat: {user_lat:.6f}°",
        f"Lon: {user_lon:.6f}°",
        f"Alt: {user_alt:.1f}m"
    ]
    
    line_height = 36
    for i, line in enumerate(info_lines):
        txt = FONT_SMALL.render(line, True, FG)
        surf.blit(txt, (x, y + i * line_height))

def draw_satellite_info(surf, x, y):
    """Draw satellite information"""
    if satellite_info is None:
        txt = FONT_SMALL.render("No satellite tracked", True, ERR)
        surf.blit(txt, (x, y))
        return
    
    info_lines = [
        f"Satellite: {satellite_info['name'][:20]}",
        f"Distance: {satellite_info['distance_km']:.1f} km",
        f"Bearing: {satellite_info['bearing']:.1f}°"
    ]
    
    line_height = 32
    for i, line in enumerate(info_lines):
        txt = FONT_SMALL.render(line, True, ACCENT)
        surf.blit(txt, (x, y + i * line_height))

def ecef_to_geodetic(x_km, y_km, z_km):
    """Convert ECEF coordinates (km) to geodetic (lat, lon in degrees)"""
    # WGS84 constants
    a = 6378.137  # km
    f = 1.0 / 298.257223563
    e2 = f * (2 - f)
    
    # Calculate longitude
    lon_rad = math.atan2(y_km, x_km)
    
    # Calculate latitude (iterative)
    p = math.sqrt(x_km**2 + y_km**2)
    lat_rad = math.atan2(z_km, p * (1 - e2))
    
    # Iterate to refine latitude
    for _ in range(5):
        N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
        lat_rad = math.atan2(z_km + e2 * N * math.sin(lat_rad), p)
    
    return math.degrees(lat_rad), math.degrees(lon_rad)

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing from point 1 to point 2 in degrees (0=North, 90=East)"""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon_r = math.radians(lon2 - lon1)
    
    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)
    bearing = math.atan2(x, y)
    
    bearing_deg = (math.degrees(bearing) + 360) % 360
    return bearing_deg

def draw_bearing_arrow(surf, center_x, center_y, radius, satellite_bearing):
    """
    Draw an arrow pointing to the satellite relative to device heading.
    
    The arrow rotates to always point toward the satellite, compensating
    for the device's current heading from the compass.
    
    Args:
        surf: pygame surface
        center_x, center_y: center of arrow circle
        radius: length of arrow from center to tip
        satellite_bearing: absolute bearing to satellite in degrees (0 = North)
    """
    # Get current device heading from compass
    try:
        heading = compass.get_heading()
    except Exception as e:
        print(f"Error reading compass: {e}")
        heading = 0  # Fallback to north if compass fails
    
    # Calculate relative angle between device heading and satellite
    # This gives us the direction to point relative to where device is facing
    relative_angle = satellite_bearing - heading
    
    # Normalize to -180 to 180 range for shortest rotation
    while relative_angle > 180:
        relative_angle -= 360
    while relative_angle < -180:
        relative_angle += 360
    
    # Convert to radians for trig functions
    # Note: In screen coordinates, Y increases downward, so we negate for proper rotation
    angle_rad = math.radians(relative_angle)
    
    # Calculate arrow tip position
    # Using standard unit circle: angle 0 points right, 90 points up
    # We want 0 to point up (north), so we subtract 90 degrees (π/2 radians)
    adjusted_angle = angle_rad - math.pi / 2
    
    tip_x = center_x + radius * math.cos(adjusted_angle)
    tip_y = center_y + radius * math.sin(adjusted_angle)
    
    # Draw arrow shaft (thick line from center to tip)
    pygame.draw.line(surf, ACCENT, (center_x, center_y), (tip_x, tip_y), 8)
    
    # Draw arrowhead (triangle at tip)
    arrow_head_size = 25
    arrow_angle = 150  # degrees for arrowhead wings
    
    # Left wing of arrowhead
    left_angle = adjusted_angle + math.radians(arrow_angle)
    left_x = tip_x + arrow_head_size * math.cos(left_angle)
    left_y = tip_y + arrow_head_size * math.sin(left_angle)
    
    # Right wing of arrowhead
    right_angle = adjusted_angle - math.radians(arrow_angle)
    right_x = tip_x + arrow_head_size * math.cos(right_angle)
    right_y = tip_y + arrow_head_size * math.sin(right_angle)
    
    # Draw filled triangle for arrowhead
    pygame.draw.polygon(surf, ACCENT, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)])
    
    # Optional: Draw a circle at center for reference
    pygame.draw.circle(surf, ACCENT, (center_x, center_y), 8)
    
    # Optional: Display numeric bearing information
    bearing_text = FONT_SMALL.render(f"{satellite_bearing:.0f}°", True, ACCENT)
    text_rect = bearing_text.get_rect(center=(center_x, center_y - radius - 30))
    surf.blit(bearing_text, text_rect)
    
    # Display relative angle (how much to turn)
    relative_text = FONT_SMALL.render(f"Turn: {relative_angle:+.0f}°", True, FG)
    text_rect2 = relative_text.get_rect(center=(center_x, center_y + radius + 30))
    surf.blit(relative_text, text_rect2)

def update_satellite_position():
    """Update the nearest satellite position"""
    global satellite_info, last_satellite_update
    
    current_time = time.time()
    
    if current_time - last_satellite_update < SATELLITE_UPDATE_INTERVAL:
        return
    
    if satellite_service is None:
        return
    
    try:
        when = datetime.now(timezone.utc)
        sat_data = satellite_service.find_nearest_satellite(
            user_lat, user_lon, user_alt, when=when
        )
        print(f"Nearest satellite data: {sat_data}")
        
        if sat_data:
            ecef = sat_data.get("position_ecef_km", [0, 0, 0])
            sat_lat, sat_lon = ecef_to_geodetic(ecef[0], ecef[1], ecef[2])
            
            satellite_info = {
                "name": sat_data.get("name", "Unknown").strip(),
                "lat": sat_lat,
                "lon": sat_lon,
                "distance_km": sat_data.get("distance_km", 0),
                "bearing": calculate_bearing(user_lat, user_lon, sat_lat, sat_lon)
            }
            print(f"Satellite updated: {satellite_info['name']}, bearing: {satellite_info['bearing']:.1f}°, distance: {satellite_info['distance_km']:.1f}km")
        else:
            satellite_info = None
            print("No satellite found")
        
        last_satellite_update = current_time
        
    except Exception as e:
        print(f"Error updating satellite position: {e}")
        satellite_info = None

def update_gps_position():
    """Update user position from GPS module"""
    global user_lat, user_lon, user_alt, user_pdop
    pass

def post_payload(answers):
    # Build mode based on first answer
    in_danger = answers.get("in_danger", "no")
    
    payload = {
        "deviceId": DEVICE_ID,
        "ts": datetime.now(timezone.utc).isoformat(),
        "lat": user_lat,
        "lon": user_lon,
        "mode": "SOS" if in_danger == "yes" else "OK",
        "pdop": user_pdop,
        "answers": answers
    }
    print(f"Posting payload: {json.dumps(payload)}")
    try:
        r = requests.post(f"{API_BASE}/api/pings", 
                         headers={"Content-Type":"application/json"}, 
                         data=json.dumps(payload), 
                         timeout=3)
        return r.ok
    except Exception:
        return False

# ====== APP STATE ======
mode = "START"  # START, ALIGN, DANGER, EMERGENCY, CHECKIN, SENDING, SENT, ERROR
answers = {}

# Button layout
pad = 24
btn_w = W//2 - pad*2
btn_h = 90
y_btn = H - btn_h - pad

# Create buttons (we'll position them as needed)
def make_button(x, y, w, h, label, color):
    return Button((x, y, w, h), label, color)

clock = pygame.time.Clock()

# ====== RENDER FUNCTIONS ======
def render_start():
    """Initial welcome screen"""
    screen.fill(BG)
    
    draw_text_center("Begin Search", H//2 - 100, ACCENT)
    
    # Center start button
    btn_w_center = 300
    btn = make_button(W//2 - btn_w_center//2, H//2 + 50, btn_w_center, btn_h, "START", OK)
    btn.draw(screen)
    return [btn]

def render_align():
    """Enhanced satellite alignment screen with compass visualization"""
    screen.fill(BG)
    
    # Title
    draw_text_center("Align with Satellite", 60, ACCENT)
    
    if satellite_info:
        # Main arrow pointing to satellite
        center_x, center_y = W//2, H//2
        arrow_radius = 180
        
        # Draw compass circle background
        pygame.draw.circle(screen, (30, 35, 45), (center_x, center_y), arrow_radius + 20, 3)
        
        # Draw cardinal direction markers
        marker_radius = arrow_radius + 40
        for angle, label in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
            angle_rad = math.radians(angle - 90)  # Adjust so 0 is North
            marker_x = center_x + marker_radius * math.cos(angle_rad)
            marker_y = center_y + marker_radius * math.sin(angle_rad)
            
            marker_txt = FONT.render(label, True, FG)
            marker_rect = marker_txt.get_rect(center=(marker_x, marker_y))
            screen.blit(marker_txt, marker_rect)
        
        # Draw the arrow pointing to satellite
        draw_bearing_arrow(screen, center_x, center_y, arrow_radius, satellite_info['bearing'])
        
        # Display satellite info
        info_y = center_y + arrow_radius + 100
        sat_name = satellite_info['name'].strip()
        name_txt = FONT.render(f"Target: {sat_name[:20]}", True, ACCENT)
        screen.blit(name_txt, name_txt.get_rect(center=(W//2, info_y)))
        
        dist_txt = FONT_SMALL.render(
            f"Distance: {satellite_info['distance_km']:.1f} km", 
            True, FG
        )
        screen.blit(dist_txt, dist_txt.get_rect(center=(W//2, info_y + 40)))
        
        # Compass heading info
        try:
            current_heading = compass.get_heading()
            direction = compass.get_cardinal_direction()
            
            heading_txt = FONT_SMALL.render(
                f"Your heading: {current_heading:.0f}° ({direction})", 
                True, FG
            )
            screen.blit(heading_txt, heading_txt.get_rect(center=(W//2, info_y + 75)))
            
            # Calculate and show how much to turn
            turn_amount = satellite_info['bearing'] - current_heading
            while turn_amount > 180:
                turn_amount -= 360
            while turn_amount < -180:
                turn_amount += 360
            
            if abs(turn_amount) < 10:
                turn_txt = FONT_SMALL.render("✓ ALIGNED!", True, OK)
            else:
                turn_direction = "RIGHT" if turn_amount > 0 else "LEFT"
                turn_txt = FONT_SMALL.render(
                    f"Turn {turn_direction} {abs(turn_amount):.0f}°", 
                    True, WARN
                )
            screen.blit(turn_txt, turn_txt.get_rect(center=(W//2, info_y + 110)))
            
        except Exception as e:
            err_txt = FONT_SMALL.render(f"Compass error: {e}", True, ERR)
            screen.blit(err_txt, err_txt.get_rect(center=(W//2, info_y + 75)))
    else:
        # No satellite found
        draw_text_center("Searching for satellite...", H//2 - 50, WARN)
        
        # Add a loading animation
        dots = "." * (int(time.time() * 2) % 4)
        loading_txt = FONT.render(f"Please wait{dots}", True, FG)
        screen.blit(loading_txt, loading_txt.get_rect(center=(W//2, H//2 + 20)))
    
    # Continue button
    btn_w_center = 300
    btn = make_button(W//2 - btn_w_center//2, H - btn_h - pad, btn_w_center, btn_h, "CONTINUE", ACCENT)
    btn.draw(screen)
    return [btn]

def render_danger_question():
    """First question: Are you in danger?"""
    screen.fill(BG)
    
    # Draw location and satellite info
    draw_location_info(screen, 20, 20)
    draw_satellite_info(screen, W - 280, 20)
    
    draw_text_center("Are you in danger?", H//2 - 100, ACCENT)
    
    btn_yes = make_button(pad, y_btn, btn_w, btn_h, "YES", ERR)
    btn_no = make_button(W - pad - btn_w, y_btn, btn_w, btn_h, "NO", OK)
    
    btn_yes.draw(screen)
    btn_no.draw(screen)
    
    return [btn_yes, btn_no]

def render_emergency_questions(question_idx):
    """Emergency questions (after YES to danger)"""
    questions = [
        "Are you injured?",
        "Are you alone?",
        "Is threat active?"
    ]
    
    screen.fill(BG)
    
    # Draw location and satellite info
    draw_location_info(screen, 20, 20)
    draw_satellite_info(screen, W - 280, 20)
    
    draw_text_center(questions[question_idx], H//2 - 100, ACCENT)
    
    btn_yes = make_button(pad, y_btn, btn_w, btn_h, "YES", ERR)
    btn_no = make_button(W - pad - btn_w, y_btn, btn_w, btn_h, "NO", OK)
    
    btn_yes.draw(screen)
    btn_no.draw(screen)
    
    return [btn_yes, btn_no]

def render_checkin_options():
    """Non-emergency options (after NO to danger)"""
    screen.fill(BG)
    
    # Draw location and satellite info
    draw_location_info(screen, 20, 20)
    draw_satellite_info(screen, W - 280, 20)
    
    draw_text_center("Select status", H//2 - 150, ACCENT)
    
    # Three buttons stacked vertically
    btn_h_check = 80
    spacing = 20
    start_y = H//2 - 60
    btn_w_check = 400
    x_center = W//2 - btn_w_check//2
    
    btn1 = make_button(x_center, start_y, btn_w_check, btn_h_check, "Checking In", ACCENT)
    btn2 = make_button(x_center, start_y + btn_h_check + spacing, btn_w_check, btn_h_check, "Low Battery", WARN)
    btn3 = make_button(x_center, start_y + 2*(btn_h_check + spacing), btn_w_check, btn_h_check, "Doing Good", OK)
    
    btn1.draw(screen)
    btn2.draw(screen)
    btn3.draw(screen)
    
    return [btn1, btn2, btn3]

def render_sending():
    """Sending data screen"""
    screen.fill(BG)
    draw_text_center("Sending message...", H//2, ACCENT)

def render_sent():
    """Success screen"""
    screen.fill(BG)
    draw_text_center("Message sent successfully", H//2 - 50, OK)
    
    btn_w_center = 300
    btn = make_button(W//2 - btn_w_center//2, H//2 + 50, btn_w_center, btn_h, "NEW MESSAGE", ACCENT)
    btn.draw(screen)
    return [btn]

def render_error():
    """Error screen"""
    screen.fill(BG)
    draw_text_center("Send failed", H//2 - 80, ERR)
    draw_text_center("Please try again", H//2, FG, FONT)
    
    btn_w_center = 300
    btn_retry = make_button(W//2 - btn_w_center//2, H//2 + 80, btn_w_center, btn_h, "RETRY", ACCENT)
    btn_retry.draw(screen)
    return [btn_retry]

# ====== MAIN LOOP ======
emergency_q_idx = 0
buttons = []

# Do initial satellite update
update_satellite_position()

try:
    while True:
        # Update positions
        update_gps_position()
        update_satellite_position()
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    pygame.quit()
                    raise SystemExit
            
            if e.type == pygame.MOUSEBUTTONDOWN:
                x, y = e.pos
                
                if mode == "START":
                    if buttons[0].hit((x, y)):
                        mode = "ALIGN"
                        
                elif mode == "ALIGN":
                    if buttons[0].hit((x, y)):
                        mode = "DANGER"
                        
                elif mode == "DANGER":
                    if buttons[0].hit((x, y)):  # YES
                        answers["in_danger"] = "yes"
                        emergency_q_idx = 0
                        mode = "EMERGENCY"
                    elif buttons[1].hit((x, y)):  # NO
                        answers["in_danger"] = "no"
                        mode = "CHECKIN"
                        
                elif mode == "EMERGENCY":
                    questions_keys = ["injured", "alone", "threat_active"]
                    if buttons[0].hit((x, y)):  # YES
                        answers[questions_keys[emergency_q_idx]] = "yes"
                        emergency_q_idx += 1
                    elif buttons[1].hit((x, y)):  # NO
                        answers[questions_keys[emergency_q_idx]] = "no"
                        emergency_q_idx += 1
                    
                    if emergency_q_idx >= 3:
                        mode = "SENDING"
                        pygame.display.flip()
                        ok = post_payload(answers)
                        mode = "SENT" if ok else "ERROR"
                        
                elif mode == "CHECKIN":
                    if buttons[0].hit((x, y)):  # Checking In
                        answers["status"] = "checking_in"
                        mode = "SENDING"
                    elif buttons[1].hit((x, y)):  # Low Battery
                        answers["status"] = "low_battery"
                        mode = "SENDING"
                    elif buttons[2].hit((x, y)):  # Doing Good
                        answers["status"] = "doing_good"
                        mode = "SENDING"
                    
                    if mode == "SENDING":
                        pygame.display.flip()
                        ok = post_payload(answers)
                        mode = "SENT" if ok else "ERROR"
                        
                elif mode == "SENT":
                    if buttons[0].hit((x, y)):  # NEW MESSAGE
                        # Reset to start
                        mode = "START"
                        answers = {}
                        emergency_q_idx = 0
                        
                elif mode == "ERROR":
                    if buttons[0].hit((x, y)):  # RETRY
                        # Reset to start instead of retrying
                        mode = "START"
                        answers = {}
                        emergency_q_idx = 0
        
        # Render current screen
        if mode == "START":
            buttons = render_start()
        elif mode == "ALIGN":
            buttons = render_align()
        elif mode == "DANGER":
            buttons = render_danger_question()
        elif mode == "EMERGENCY":
            buttons = render_emergency_questions(emergency_q_idx)
        elif mode == "CHECKIN":
            buttons = render_checkin_options()
        elif mode == "SENDING":
            render_sending()
            buttons = []
        elif mode == "SENT":
            buttons = render_sent()
        elif mode == "ERROR":
            buttons = render_error()
        
        pygame.display.flip()
        clock.tick(60)

finally:
    # Clean shutdown
    print("\nShutting down...")
    if scheduler is not None:
        scheduler.stop()
    pygame.quit()