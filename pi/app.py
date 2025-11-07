import json, time, requests
from datetime import datetime, timezone

import pygame
pygame.init()

API_BASE = "http://192.168.137.1:4000"
DEVICE_ID = "autosat-01"

QUESTIONS = [
    "Are you hurt?",
    "Do you need shelter?",
    "Are you with children?"
]

# If you have GPS/PDOP values, set them here before sending
DEFAULT_LAT = 43.7315
DEFAULT_LON = -79.7624
DEFAULT_PDOP = 2.9

# ====== UI PRIMITIVES ======
W, H = pygame.display.Info().current_w, pygame.display.Info().current_h
screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
FONT  = pygame.font.SysFont(None, 40)
FONT_BIG = pygame.font.SysFont(None, 48)
BG = (8,10,14)
FG = (220,230,255)
ACCENT = (70,130,255)
OK = (60,180,120)
ERR = (220,80,80)

class Button:
    def __init__(self, rect, label, color):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=14)
        txt = FONT_BIG.render(self.label, True, (0,0,0))
        surf.blit(txt, txt.get_rect(center=self.rect.center))
    def hit(self, pos):
        return self.rect.collidepoint(pos)

def draw_text_center(lines, y, color=FG):
    for i, line in enumerate(lines):
        txt = FONT_BIG.render(line, True, color)
        screen.blit(txt, txt.get_rect(center=(W//2, y + i*56)))

def post_payload(answers):
    payload = {
        "deviceId": DEVICE_ID,
        "ts": datetime.now(timezone.utc).isoformat(),
        "lat": DEFAULT_LAT,
        "lon": DEFAULT_LON,
        "mode": "SOS" if answers[0]["a"]=="yes" else "OK",
        "pdop": DEFAULT_PDOP,
        "answers": answers
    }
    try:
        r = requests.post(f"{API_BASE}/api/pings", headers={"Content-Type":"application/json"}, data=json.dumps(payload), timeout=3)
        return r.ok
    except Exception:
        return False

# ====== APP STATE ======
q_idx = 0
answers = []  # list of {"q": "...", "a": "yes|no"}
status = ""   # "", "sending", "sent", "error"

# layout
pad = 24
btn_w = W//2 - pad*2
btn_h = 90
y_btn = H - btn_h - pad
btn_yes = Button((pad, y_btn, btn_w, btn_h), "YES", OK)
btn_no  = Button((W - pad - btn_w, y_btn, btn_w, btn_h), "NO", ERR)
btn_send = Button((W//2 - btn_w//2, y_btn, btn_w, btn_h), "SEND", ACCENT)
btn_reset= Button((W//2 - btn_w//2, y_btn, btn_w, btn_h), "NEW", ACCENT)

clock = pygame.time.Clock()

def render_question():
    screen.fill(BG)
    draw_text_center(["Answer the question:"], 80, ACCENT)
    draw_text_center([QUESTIONS[q_idx]], 160, FG)
    btn_yes.draw(screen)
    btn_no.draw(screen)

def render_review():
    screen.fill(BG)
    draw_text_center(["Review answers"], 60, ACCENT)
    y = 140
    for qa in answers:
        line = f"{qa['q']}  →  {qa['a'].upper()}"
        txt = FONT.render(line, True, FG)
        screen.blit(txt, (pad, y))
        y += 44
    btn_send.draw(screen)

def render_status():
    screen.fill(BG)
    if status == "sending":
        draw_text_center(["Sending…"], H//2 - 20, ACCENT)
    elif status == "sent":
        draw_text_center(["Sent successfully"], H//2 - 20, OK)
        btn_reset.draw(screen)
    elif status == "error":
        draw_text_center(["Send failed"], H//2 - 60, ERR)
        btn_send.draw(screen)

mode = "QA"  # "QA" → "REVIEW" → "STATUS"

# ====== MAIN LOOP ======
while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); raise SystemExit
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_q: pygame.quit(); raise SystemExit
        if e.type == pygame.MOUSEBUTTONDOWN:
            x,y = e.pos
            if mode == "QA":
                if btn_yes.hit((x,y)):
                    answers.append({"q": QUESTIONS[q_idx], "a": "yes"})
                    q_idx += 1
                elif btn_no.hit((x,y)):
                    answers.append({"q": QUESTIONS[q_idx], "a": "no"})
                    q_idx += 1
                if q_idx >= len(QUESTIONS):
                    mode = "REVIEW"
            elif mode == "REVIEW":
                if btn_send.hit((x,y)):
                    mode = "STATUS"; status = "sending"
                    pygame.display.flip()
                    ok = post_payload(answers)
                    status = "sent" if ok else "error"
            elif mode == "STATUS":
                if status == "sent" and btn_reset.hit((x,y)):
                    # reset flow
                    q_idx = 0; answers = []; mode = "QA"; status = ""

    if mode == "QA":
        render_question()
    elif mode == "REVIEW":
        render_review()
    else:
        render_status()

    pygame.display.flip()
    clock.tick(60)
