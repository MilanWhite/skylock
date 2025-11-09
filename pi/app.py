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
SATELLITE_UPDATE_INTERVAL = 5  # Update every 5 seconds

# Initialize satellite service with scheduler
try:
    repo = SqliteTleRepository()
    scheduler = TleSchedulerService(repo, tle_group="amateur", interval_seconds=3600)
    satellite_service = Sgp4SatelliteService(repo)
    
    # Start scheduler with initial fetch
    print("Starting scheduler and fetching initial TLE data...")
    scheduler.start(initial_fetch=True)
    
    # Wait longer for initial fetch to lete
    print("Waiting for TLE data to be fetched...")
    max_wait = 30  # Wait up to 30 seconds
    waited = 0
    while waited < max_wait:
        time.sleep(1)
        waited += 1
        # Try to see if we have any data
        try:
            test_data = repo.fetch_all_tles()
            if test_data and len(test_data) > 0:
                print(f"TLE data loaded! Found {len(test_data)} satellites")
                break
        except Exception:
            pass
    
    if waited >= max_wait:
        print("Warning: Timeout waiting for TLE data")
    
    print("Satellite service initialized successfully")
except Exception as e:
    print(f"Failed to initialize satellite service: {e}")
    import traceback
    traceback.print_exc()
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
    """Satellite alignment instruction screen"""
    screen.fill(BG)
    
    if satellite_info:
        draw_text_center("Face device to satellite", H//2 - 100, ACCENT)
        sat_name = satellite_info['name'][:25]  # Truncate if too long
        draw_text_center(sat_name, H//2, FG, FONT_MED)
        draw_text_center(f"Bearing: {satellite_info['bearing']:.1f}°", H//2 + 60, ACCENT, FONT)
        draw_text_center(f"Distance: {satellite_info['distance_km']:.1f} km", H//2 + 100, ACCENT, FONT)
    else:
        draw_text_center("Searching for satellite...", H//2 - 50, WARN)
    
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