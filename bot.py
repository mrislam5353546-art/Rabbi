import telebot
from telebot import types
import json
import os
import re
import time
import threading
import requests
import phonenumbers
import random
import csv
import io
import openpyxl
import xlrd
from phonenumbers import region_code_for_number, geocoder

# ── PID management ────────────────────────────────────────────────────────────
_PID_FILE = "/tmp/ar_otp_bot.pid"
_my_pid = os.getpid()
if os.path.exists(_PID_FILE):
    try:
        _old_pid = int(open(_PID_FILE).read().strip())
        if _old_pid != _my_pid:
            try:
                os.kill(_old_pid, 9)
                time.sleep(1)
                print(f"[START] Killed old instance PID {_old_pid}")
            except ProcessLookupError:
                pass
    except Exception:
        pass
open(_PID_FILE, "w").write(str(_my_pid))

API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
POLL_INTERVAL = 8
SUPER_ADMIN_ID = 8523774444

# ── File paths ────────────────────────────────────────────────────────────────
ADMINS_FILE        = "admins.json"
USER_SETTINGS_FILE = "user_settings.json"
USER_PANELS_FILE   = "user_panels.json"
USER_SERVICES_FILE = "user_services.json"
STOCK_FILE         = "stock_data.json"
USERS_FILE         = "users.json"
SEEN_FILE          = "seen_otps.json"
USER_NAMES_FILE    = "user_names.json"

DEFAULT_USER_SETTINGS = {
    "group_id":             None,
    "group_link":           "",
    "bot_link":             "",
    "channel2":             "",
    "brand_name":           "AR TEAM",
    "auto_delete":          True,
    "auto_delete_seconds":  3600,
}

DEFAULT_SERVICES = [
    {"label": "Instagram →", "key": "instagram"},
    {"label": "Facebook 💎", "key": "facebook"},
    {"label": "WhatsApp",    "key": "whatsapp"},
    {"label": "PC Clone 💎", "key": "pc clone"},
]

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=40)

# ── JSON helpers ──────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ── Admin management ──────────────────────────────────────────────────────────

def _load_admins():
    data = load_json(ADMINS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    if str(SUPER_ADMIN_ID) not in data:
        data[str(SUPER_ADMIN_ID)] = {"expiry": None, "added_by": SUPER_ADMIN_ID, "days": None}
        save_json(ADMINS_FILE, data)
    return data

def _save_admins(data):
    save_json(ADMINS_FILE, data)

def is_admin(uid):
    admins = _load_admins()
    uid_str = str(uid)
    if uid_str not in admins:
        return False
    expiry = admins[uid_str].get("expiry")
    return True if expiry is None else time.time() < expiry

def get_admin_expiry_str(uid):
    admins = _load_admins()
    info = admins.get(str(uid), {})
    expiry = info.get("expiry")
    if expiry is None:
        return "♾️ Permanent"
    remaining = expiry - time.time()
    if remaining <= 0:
        return "❌ Expired"
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    return f"⏳ {days}d {hours}h remaining"

def add_admin(uid, days=None, added_by=None):
    if uid == SUPER_ADMIN_ID:
        return False
    admins = _load_admins()
    expiry = time.time() + days * 86400 if days else None
    admins[str(uid)] = {
        "expiry": expiry,
        "added_by": added_by or SUPER_ADMIN_ID,
        "days": days,
        "added_at": time.time(),
    }
    _save_admins(admins)
    return True

def remove_admin(uid):
    if uid == SUPER_ADMIN_ID:
        return False
    admins = _load_admins()
    if str(uid) in admins:
        del admins[str(uid)]
        _save_admins(admins)
        return True
    return False

def auto_expire_admins():
    while True:
        try:
            admins = _load_admins()
            changed = False
            for uid_str, info in list(admins.items()):
                if uid_str == str(SUPER_ADMIN_ID):
                    continue
                expiry = info.get("expiry")
                if expiry and time.time() >= expiry:
                    del admins[uid_str]
                    changed = True
                    print(f"[ADMIN] Auto-expired: {uid_str}")
                    try:
                        bot.send_message(int(uid_str),
                            "⏰ <b>আপনার Admin মেয়াদ শেষ!</b>\n\n"
                            "Bot আর ব্যবহার করতে পারবেন না।\n"
                            "Admin-এর সাথে যোগাযোগ করুন।",
                            parse_mode="HTML")
                    except Exception:
                        pass
            if changed:
                _save_admins(admins)
        except Exception as e:
            print(f"[EXPIRE] Error: {e}")
        time.sleep(60)

# ── Per-user settings ─────────────────────────────────────────────────────────

def get_user_settings(uid):
    data = load_json(USER_SETTINGS_FILE, {})
    settings = data.get(str(uid), {})
    return {**DEFAULT_USER_SETTINGS, **settings}

def save_user_settings(uid, settings):
    data = load_json(USER_SETTINGS_FILE, {})
    data[str(uid)] = settings
    save_json(USER_SETTINGS_FILE, data)

def update_user_setting(uid, key, value):
    s = get_user_settings(uid)
    s[key] = value
    save_user_settings(uid, s)

# ── Per-user panels ───────────────────────────────────────────────────────────

def get_user_panels(uid):
    data = load_json(USER_PANELS_FILE, {})
    return data.get(str(uid), [])

def save_user_panels(uid, panels):
    data = load_json(USER_PANELS_FILE, {})
    data[str(uid)] = panels
    save_json(USER_PANELS_FILE, data)

# ── Per-user services ─────────────────────────────────────────────────────────

def get_user_services(uid):
    data = load_json(USER_SERVICES_FILE, {})
    return data.get(str(uid), list(DEFAULT_SERVICES))

def save_user_services(uid, services):
    data = load_json(USER_SERVICES_FILE, {})
    data[str(uid)] = services
    save_json(USER_SERVICES_FILE, data)

# ── Global state ──────────────────────────────────────────────────────────────

stock = load_json(STOCK_FILE, {
    "whatsapp": {}, "facebook": {}, "telegram": {},
    "instagram": {}, "pc clone": {}, "binance": {},
})
users      = load_json(USERS_FILE, [])
seen_otps  = load_json(SEEN_FILE, {})
user_names = load_json(USER_NAMES_FILE, {})

user_map       = {}
user_map_lock  = threading.Lock()
assigned_time  = {}
assigned_admin = {}

seen_lock    = threading.Lock()
_panel_stats = {}
_stats_lock  = threading.Lock()

_dynamic_sessions = {}
_dynamic_locks    = {}
_addpanel_state   = {}
_pending_excel    = {}
_addservice_state = {}
_countdowns       = {}

_demo_active = False
_demo_lock   = threading.Lock()
_demo_config = {"numbers": ["8801700000000"], "digits": 6, "service": "Facebook", "interval": 30}

_pending_add_admin = {}   # uid → {target_uid, days}

# ── Stock ─────────────────────────────────────────────────────────────────────

def save_stock():
    save_json(STOCK_FILE, stock)

# ── Users ─────────────────────────────────────────────────────────────────────

def register_user(chat_id, first_name="", last_name="", username=""):
    if chat_id not in users:
        users.append(chat_id)
        save_json(USERS_FILE, users)
    full = f"{first_name} {last_name}".strip()
    if full and username:
        display = f"{full} (@{username})"
    elif full:
        display = full
    elif username:
        display = f"@{username}"
    else:
        display = None
    if display:
        user_names[str(chat_id)] = display
        save_json(USER_NAMES_FILE, user_names)

def register_number(user_id, number, admin_uid=None):
    clean = re.sub(r"\D", "", str(number))
    with user_map_lock:
        user_map[clean] = user_id
        assigned_time[clean] = time.time()
        if admin_uid is not None:
            assigned_admin[clean] = admin_uid

def mask_number(number):
    s = str(number)
    if len(s) <= 9:
        return s[:3] + "***" + s[-3:]
    return s[:6] + "***" + s[-3:]

# ── Country helpers ───────────────────────────────────────────────────────────

def get_country_details(num_str):
    try:
        num_str = str(num_str).strip()
        if not num_str.startswith("+"):
            num_str = "+" + num_str
        parsed = phonenumbers.parse(num_str)
        cc = region_code_for_number(parsed)
        name = geocoder.description_for_number(parsed, "en")
        flag = "".join(chr(ord(c.upper()) + 127397) for c in cc)
        return name, flag
    except Exception:
        return "Unknown", "🌐"

# ── OTP messaging ─────────────────────────────────────────────────────────────

def get_brand_name(admin_uid):
    if admin_uid is not None:
        return get_user_settings(admin_uid).get("brand_name", "AR TEAM")
    return "AR TEAM"

def _try_delete(chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def send_otp_message(chat_id, otp, number, seconds, service="", admin_uid=None, is_group=False):
    svc   = service.upper() if service else "—"
    c_name, flag = get_country_details(number)
    brand = get_brand_name(admin_uid)

    message = (
        "🌟══════════════🌟\n"
        "✨ <b>OTP Received</b> ✨\n\n"
        f"⚙ <b>Service:</b> {svc}\n"
        f"☎ <b>Number:</b> <code>{mask_number(number)}</code>\n"
        f"🌍 <b>Country:</b> {c_name} {flag}\n\n"
        f"📲 <b>OTP Code:</b> <code>{otp}</code>\n\n"
        "🌟══════════════🌟\n\n"
        f"🌟 <i>Powered by</i>  <b>{brand}</b> 🌟"
    )

    if is_group and admin_uid is not None:
        s = get_user_settings(admin_uid)
        markup = types.InlineKeyboardMarkup()
        btns = []
        if s.get("bot_link"):
            btns.append(types.InlineKeyboardButton("🤖 Number Bot", url=s["bot_link"]))
        if s.get("channel2"):
            btns.append(types.InlineKeyboardButton("📢 Main Channel", url=s["channel2"]))
        if btns:
            markup.row(*btns)
        try:
            sent = bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML", reply_markup=markup)
            if s.get("auto_delete"):
                delay = s.get("auto_delete_seconds", 3600)
                threading.Timer(delay, lambda: _try_delete(chat_id, sent.message_id)).start()
        except Exception as e:
            print(f"[OTP] Group send error to {chat_id}: {e}")
    else:
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
        except Exception as e:
            print(f"[OTP] User send error to {chat_id}: {e}")

def _dispatch_otp(otp, number, seconds, service="", admin_uid=None):
    if admin_uid is not None:
        s = get_user_settings(admin_uid)
        gid = s.get("group_id")
        if gid:
            send_otp_message(gid, otp, number, seconds, service, admin_uid=admin_uid, is_group=True)
    clean = re.sub(r"\D", "", str(number))
    with user_map_lock:
        uid = user_map.pop(clean, None)
        assigned_time.pop(clean, None)
        assigned_admin.pop(clean, None)
    if uid:
        send_otp_message(uid, otp, number, seconds, service, admin_uid=admin_uid)

# ── OTP processing ────────────────────────────────────────────────────────────

def extract_otp_from_sms(sms_text):
    cleaned = re.sub(r"(?<=\d) (?=\d)", "", sms_text)
    m = re.search(r"\b(\d{4,8})\b", cleaned)
    return m.group(1) if m else None

def process_new_otps(current, admin_uid=None):
    global seen_otps
    for key, (number, otp, sms_txt, service) in current.items():
        with seen_lock:
            if key in seen_otps:
                continue
            seen_otps[key] = True
            save_json(SEEN_FILE, seen_otps)
        clean = re.sub(r"\D", "", str(number))
        with user_map_lock:
            t_start = assigned_time.get(clean)
        seconds = int(time.time() - t_start) if t_start else 0
        _dispatch_otp(otp, number, seconds, service, admin_uid=admin_uid)
        print(f"[OTP] ✅ OTP={otp} number={number} service={service} admin={admin_uid}")

# ── Panel stats ───────────────────────────────────────────────────────────────

def _record_fetch(pid, count):
    with _stats_lock:
        if pid in _panel_stats:
            _panel_stats[pid].update({"status": "🟢", "count": count, "last": time.time(), "errors": 0})

def _record_error(pid):
    with _stats_lock:
        if pid in _panel_stats:
            _panel_stats[pid]["status"] = "🔴"
            _panel_stats[pid]["errors"] = _panel_stats[pid].get("errors", 0) + 1

# ── Dynamic panel login/fetch ─────────────────────────────────────────────────

def _get_dp_lock(pid):
    if pid not in _dynamic_locks:
        _dynamic_locks[pid] = threading.Lock()
    return _dynamic_locks[pid]

def _ints_login(panel):
    pid  = panel["id"]
    base = panel["base_url"]
    panel_type = panel.get("panel_type", "smscdr")
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(base + "/login", timeout=15, verify=False)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if m:
            answer = int(m.group(1)) + int(m.group(2))
            r2 = sess.post(base + "/signin",
                data={"username": panel["username"], "password": panel["password"], "capt": answer},
                timeout=15, allow_redirects=True, verify=False)
        else:
            r2 = sess.post(base + "/signin",
                data={"username": panel["username"], "password": panel["password"]},
                timeout=15, allow_redirects=True, verify=False)
        if "login" in r2.url.lower() and "agent" not in r2.url.lower():
            print(f"[{pid}] Login failed: {r2.url}")
            return None, None
        ep = "/agent/SMSRanges" if panel_type == "smsranges" else "/agent/SMSCDRStats"
        r3 = sess.get(base + ep, timeout=15, headers={"Referer": base + "/agent/"}, verify=False)
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        cs = re.search(r"csstr=([a-f0-9]+)", r3.text)
        token = sk.group(1) if sk else (cs.group(1) if cs else "")
        print(f"[{pid}] Logged in. token={token[:10] if token else 'none'}...")
        return sess, token
    except Exception as e:
        print(f"[{pid}] Login error: {e}")
        return None, None

def _ints_fetch(panel):
    pid  = panel["id"]
    base = panel["base_url"]
    panel_type = panel.get("panel_type", "smscdr")
    if panel_type == "smsranges":
        data_url = base + "/agent/res/data_smsranges.php"
        cdr_page = base + "/agent/SMSRanges"
    else:
        data_url = base + "/agent/res/data_smscdr.php"
        cdr_page = base + "/agent/SMSCDRStats"
    found = {}
    with _get_dp_lock(pid):
        sd = _dynamic_sessions.get(pid, {})
        if not sd.get("session"):
            s, tok = _ints_login(panel)
            if not s:
                _record_error(pid)
                return found
            _dynamic_sessions[pid] = {"session": s, "token": tok}
            sd = _dynamic_sessions[pid]
        sess  = sd["session"]
        token = sd.get("token", "")
        today = time.strftime("%Y-%m-%d")

        def build_url():
            return (
                f"{data_url}?fdate1={today}%2000:00:00&fdate2={today}%2023:59:59"
                f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0&sesskey={token}"
            )

        headers = {"Referer": cdr_page, "X-Requested-With": "XMLHttpRequest"}
        try:
            r    = sess.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if r.status_code != 200 or not body or body.startswith("<") or "Direct Script" in body:
                print(f"[{pid}] Bad response, re-logging in.")
                _dynamic_sessions[pid] = {}
                s, tok = _ints_login(panel)
                if not s:
                    _record_error(pid)
                    return found
                _dynamic_sessions[pid] = {"session": s, "token": tok}
                r    = s.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number  = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip() if len(row) > 5 else (str(row[4]).strip() if len(row) > 4 else "")
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch(pid, len(rows))
        except Exception as e:
            print(f"[{pid}] Fetch error: {e}")
            _record_error(pid)
            _dynamic_sessions[pid] = {}
    return found

def _start_panel_for_admin(panel, admin_uid):
    pid = panel["id"]
    with _stats_lock:
        _panel_stats[pid] = {
            "name":   panel.get("username", pid),
            "host":   panel.get("host", ""),
            "status": "⏳",
            "count":  0,
            "last":   None,
            "errors": 0,
            "owner":  admin_uid,
        }

    def monitor():
        global seen_otps
        print(f"[{pid}-MONITOR] Started for admin={admin_uid}. Pre-loading...")
        existing = _ints_fetch(panel)
        with seen_lock:
            for key in existing:
                seen_otps[key] = True
            save_json(SEEN_FILE, seen_otps)
        print(f"[{pid}-MONITOR] Pre-loaded {len(existing)} records. Watching...")
        while True:
            try:
                process_new_otps(_ints_fetch(panel), admin_uid=admin_uid)
            except Exception as e:
                print(f"[{pid}-MONITOR] Error: {e}")
            time.sleep(POLL_INTERVAL)

    threading.Thread(target=monitor, daemon=True).start()

# ── Demo OTP ──────────────────────────────────────────────────────────────────

def demo_monitor():
    print("[DEMO] Thread started.")
    while True:
        with _demo_lock:
            active = _demo_active
            cfg = dict(_demo_config)
        if active:
            otp    = "".join(str(random.randint(0, 9)) for _ in range(cfg["digits"]))
            number = random.choice(cfg["numbers"])
            s      = get_user_settings(SUPER_ADMIN_ID)
            gid    = s.get("group_id")
            if gid:
                try:
                    send_otp_message(gid, otp, number, "—", cfg["service"], admin_uid=SUPER_ADMIN_ID, is_group=True)
                except Exception as e:
                    print(f"[DEMO] Error: {e}")
        time.sleep(cfg["interval"])

def demo_status_text():
    with _demo_lock:
        active = _demo_active
        cfg = dict(_demo_config)
    status   = "🟢 <b>RUNNING</b>" if active else "🔴 <b>STOPPED</b>"
    nums     = cfg["numbers"]
    num_lines = ""
    for n in nums[:10]:
        c_name, flag = get_country_details(n)
        num_lines += f"  • <code>{n}</code>  {flag} {c_name}\n"
    if len(nums) > 10:
        num_lines += f"  ... +{len(nums) - 10} more\n"
    return (
        f"🎭🔥 <b>DEMO OTP PANEL</b> 🔥🎭\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"📡 <b>Status   ▸▸</b>  {status}\n"
        f"📱 <b>Numbers ({len(nums)}):</b>\n{num_lines}"
        f"🔢 <b>Digits   ▸▸</b>  {cfg['digits']}\n"
        f"💬 <b>Service  ▸▸</b>  {cfg['service']}\n"
        f"⏱️ <b>Interval ▸▸</b>  every {cfg['interval']}s\n\n"
        f"⚡━━━━━━━━━━━━━━━━⚡"
    )

def demo_menu_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    with _demo_lock:
        active = _demo_active
    m.add("⏹️ 𝗗𝗘𝗠𝗢 𝗦𝗧𝗢𝗣" if active else "▶️ 𝗗𝗘𝗠𝗢 𝗦𝗧𝗔𝗥𝗧")
    m.add("⚙️ 𝗗𝗘𝗠𝗢 𝗖𝗢𝗡𝗙𝗜𝗚")
    m.add("🔙 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟")
    return m

# ── Menus ─────────────────────────────────────────────────────────────────────

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("☎️ 𝗡𝗨𝗠𝗕𝗔𝗥 ☎️"))
    markup.add(types.KeyboardButton("📊 𝗦𝗧𝗢𝗖𝗞"), types.KeyboardButton("📞 𝗦𝗔𝗣𝗢𝗥𝗧"))
    if is_admin(user_id):
        markup.add(types.KeyboardButton("⚙️ 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 ⚙️"))
    return markup

def admin_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ 𝗡𝘂𝗺𝗯𝗮𝗿 𝗔𝗱𝗱",  "🗑️ 𝗦𝗼𝗯 𝗖𝗹𝗲𝗮𝗿")
    m.add("🔥📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", "⚡👥 𝗨𝘀𝗲𝗿 𝗖𝗼𝘂𝗻𝘁")
    m.add("📋👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁")
    m.add("🎭 𝗗𝗘𝗠𝗢 𝗢𝗧𝗣")
    m.add("➕ 𝗔𝗱𝗱 𝗣𝗮𝗻𝗲𝗹",   "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗮𝗻𝗲𝗹")
    m.add("➕ 𝗔𝗱𝗱 𝗦𝗲𝗿𝘃𝗶𝗰𝗲", "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗦𝗲𝗿𝘃𝗶𝗰𝗲")
    m.add("📊 𝗣𝗮𝗻𝗲𝗹𝘀")
    m.add("👑 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻",  "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻")
    m.add("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")
    m.add("⬅️🔙 𝗨𝘀𝗲𝗿 𝗠𝗲𝗻𝘂")
    return m

def _back_admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 Admin Panel")
    return kb

def _cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Cancel")
    return kb

def _is_back(txt):
    return (txt or "").strip() in ("🔙 Admin Panel", "❌ Cancel")

def _go_admin_panel(message, text="🔥 <b>ADMIN PANEL</b>"):
    bot.send_message(message.chat.id, text, reply_markup=admin_menu(), parse_mode="HTML")

# ── Settings helpers ──────────────────────────────────────────────────────────

def _settings_text(uid):
    s = get_user_settings(uid)
    gid    = s.get("group_id")
    g_link = s.get("group_link", "") or "❌ Set hoy nai"
    b_link = s.get("bot_link",   "") or "❌ Set hoy nai"
    ch2    = s.get("channel2",   "") or "❌ Set hoy nai"
    brand  = s.get("brand_name", "AR TEAM")
    auto_d = s.get("auto_delete", True)
    del_s  = s.get("auto_delete_seconds", 3600)
    id_str = f"<code>{gid}</code>" if gid else "❌ Set hoy nai"
    auto_str = f"🟢 ON ({del_s // 60} min)" if auto_d else "🔴 OFF"
    return (
        "⚙️ <b>BOT SETTINGS</b> ⚙️\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n\n"
        "📡 <b>OTP GROUP</b>\n"
        f"🔗 Link:        {g_link}\n"
        f"🆔 Chat ID:     {id_str}\n"
        f"⏱️ Auto Delete: {auto_str}\n\n"
        "🏷️ <b>BRAND</b>\n"
        f"✨ Brand Name:  <b>{brand}</b>\n\n"
        "📢 <b>LINKS</b>\n"
        f"📢 Main Channel: {ch2}\n"
        f"🤖 Number Bot:   {b_link}\n\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n"
        "⬇️ Ki change korte chao?"
    )

def _settings_markup(uid):
    s = get_user_settings(uid)
    auto_d = s.get("auto_delete", True)
    auto_label = "⏱️ Auto Delete: 🟢 ON" if auto_d else "⏱️ Auto Delete: 🔴 OFF"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Group Link",    callback_data="set_grplink"),
        types.InlineKeyboardButton("🆔 Group Chat ID", callback_data="set_grpid"),
    )
    markup.add(
        types.InlineKeyboardButton(auto_label,         callback_data="set_autodel"),
        types.InlineKeyboardButton("✨ Brand Name",    callback_data="set_brand"),
    )
    markup.add(
        types.InlineKeyboardButton("📢 Main Channel",  callback_data="set_channel2"),
        types.InlineKeyboardButton("🤖 Bot Link",      callback_data="set_botlink"),
    )
    return markup

def _show_settings(message):
    bot.send_message(message.chat.id, _settings_text(message.from_user.id),
                     reply_markup=_settings_markup(message.from_user.id), parse_mode="HTML")

def _show_settings_inline(call):
    try:
        bot.edit_message_text(_settings_text(call.from_user.id),
                              call.message.chat.id, call.message.message_id,
                              reply_markup=_settings_markup(call.from_user.id), parse_mode="HTML")
    except Exception:
        pass

# ── Stock ─────────────────────────────────────────────────────────────────────

def show_services(message):
    uid  = message.from_user.id
    svcs = get_user_services(uid)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btns = [types.KeyboardButton(s["label"]) for s in svcs]
    for i in range(0, len(btns), 2):
        markup.add(*btns[i:i + 2])
    markup.add(types.KeyboardButton("🔙 Main Menu"))
    bot.send_message(message.chat.id, "🛠 <b>Select Service:</b>", reply_markup=markup, parse_mode="HTML")

def show_countries(chat_id, svc):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    if svc in stock:
        for cnt, nums in stock[svc].items():
            if nums:
                _, flag = get_country_details(nums[0])
                btns.append(types.InlineKeyboardButton(f"{flag} {cnt}", callback_data=f"n:{svc}:{cnt}"))
    if btns:
        markup.add(*btns)
    markup.add(types.InlineKeyboardButton("⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_to_services"))
    bot.send_message(chat_id, f"🔥 <b>{svc.upper()} — COUNTRY SELECT</b> 🔥",
                     reply_markup=markup, parse_mode="HTML")

def _clr_service_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for svc, icon in [("facebook","💬"),("instagram","📸"),("whatsapp","📱"),
                       ("telegram","✈️"),("binance","🪙"),("pc clone","💻")]:
        total = sum(len(v) for v in stock.get(svc, {}).values())
        markup.add(types.InlineKeyboardButton(
            f"{icon} {svc.upper()} ({total})", callback_data=f"clr_s:{svc}"))
    markup.add(types.InlineKeyboardButton("☠️ Clear ALL Stock", callback_data="clr_all"))
    return markup

# ── Countdown ─────────────────────────────────────────────────────────────────

def _start_countdown(chat_id, msg_id, svc, flag, c_name, display_num, scnt, admin_uid=None):
    if chat_id in _countdowns:
        _countdowns[chat_id].set()
    cancel = threading.Event()
    _countdowns[chat_id] = cancel

    def run():
        total = 600
        while not cancel.is_set():
            mins = total // 60
            secs = total % 60
            s = get_user_settings(admin_uid) if admin_uid else {}
            grp_link = s.get("group_link", "")
            text = (
                f"✅ <b>Number Assigned Successfully!</b>\n\n"
                f"🔧 <b>Platform:</b> {svc.capitalize()}\n"
                f"🌍 <b>Country:</b> {flag} {c_name}\n\n"
                f"📞 <b>Number:</b> <code>{display_num}</code>\n\n"
                f"⏱ <b>Auto code fetch:</b> {mins:02d}:{secs:02d}s"
            )
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🔄 New Number",     callback_data=f"n:{svc}:{scnt}"),
                types.InlineKeyboardButton("🌍 Change Country", callback_data=f"s:{svc}"),
            )
            if grp_link:
                kb.add(types.InlineKeyboardButton("📢 OTP Group", url=grp_link))
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            cancel.wait(5)
            if cancel.is_set():
                break
            total -= 5
            if total < 0:
                total = 600

    threading.Thread(target=run, daemon=True).start()

# ── Broadcast ─────────────────────────────────────────────────────────────────

def make_broadcast_msg(text, brand="AR TEAM"):
    return (
        f"🔥 <b>{brand} — BROADCAST!</b> 🔥\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"📢 {text} 📢\n\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n"
        f"🤖🔥 <i>Powered by</i>  <b>{brand}</b>  🔥🤖"
    )

def do_broadcast(message):
    uid = message.from_user.id
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    brand = get_brand_name(uid)
    cap = lambda m: make_broadcast_msg(m.caption or "", brand) if m.caption else make_broadcast_msg("", brand)
    bot.send_message(message.chat.id, f"⏳🔥 <b>{len(users)} জনকে পাঠানো হচ্ছে...</b>", parse_mode="HTML")
    success = fail = 0
    for u in list(users):
        try:
            if message.photo:
                bot.send_photo(u, message.photo[-1].file_id, caption=cap(message), parse_mode="HTML")
            elif message.animation:
                bot.send_animation(u, message.animation.file_id, caption=cap(message), parse_mode="HTML")
            elif message.video:
                bot.send_video(u, message.video.file_id, caption=cap(message), parse_mode="HTML")
            elif message.video_note:
                bot.send_video_note(u, message.video_note.file_id)
            elif message.sticker:
                bot.send_sticker(u, message.sticker.file_id)
            elif message.audio:
                bot.send_audio(u, message.audio.file_id, caption=cap(message), parse_mode="HTML")
            elif message.voice:
                bot.send_voice(u, message.voice.file_id, caption=cap(message), parse_mode="HTML")
            elif message.document:
                bot.send_document(u, message.document.file_id, caption=cap(message), parse_mode="HTML")
            else:
                bot.send_message(u, make_broadcast_msg(message.text or "", brand), parse_mode="HTML")
            success += 1
        except Exception:
            fail += 1
    bot.send_message(message.chat.id,
        f"✅ <b>BROADCAST COMPLETE!</b>\n\n"
        f"✅ সফল: {success} জন\n❌ ব্যর্থ: {fail} জন",
        reply_markup=main_menu(uid), parse_mode="HTML")

# ── Excel/CSV helpers ─────────────────────────────────────────────────────────

VALID_SERVICES = ["facebook","instagram","whatsapp","telegram","binance","pc clone"]

def _parse_spreadsheet(data: bytes, filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw_rows = []
    if ext == "csv":
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            cleaned = [c.strip() for c in row if c.strip()]
            if cleaned:
                raw_rows.append(cleaned)
    elif ext == "xlsx":
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            cleaned = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cleaned:
                raw_rows.append(cleaned)
    elif ext == "xls":
        wb = xlrd.open_workbook(file_contents=data)
        ws = wb.sheet_by_index(0)
        for ri in range(ws.nrows):
            cleaned = [str(ws.cell_value(ri, ci)).strip() for ci in range(ws.ncols)
                       if str(ws.cell_value(ri, ci)).strip()]
            if cleaned:
                raw_rows.append(cleaned)
    else:
        return [], "unknown"
    if not raw_rows:
        return [], "empty"
    start = 0
    first = [c.lower() for c in raw_rows[0]]
    if any(h in first for h in ("service", "number", "phone", "mobile")):
        start = 1
    data_rows = raw_rows[start:]
    if not data_rows:
        return [], "empty"
    two_col = sum(1 for r in data_rows if len(r) >= 2)
    if two_col > len(data_rows) - two_col:
        result = []
        for r in data_rows:
            if len(r) < 2:
                continue
            col0, col1 = r[0], r[1]
            c0n = re.match(r"^\+?\d{6,15}$", re.sub(r"\s", "", col0))
            c1n = re.match(r"^\+?\d{6,15}$", re.sub(r"\s", "", col1))
            if c0n and not c1n:
                svc = col1.lower().strip(); num = re.sub(r"\D", "", col0)
            elif c1n and not c0n:
                svc = col0.lower().strip(); num = re.sub(r"\D", "", col1)
            else:
                svc = col0.lower().strip(); num = re.sub(r"\D", "", col1)
            if num and len(num) >= 7:
                result.append((svc, num))
        return result, "two_col"
    else:
        result = []
        for r in data_rows:
            num = re.sub(r"\D", "", r[0])
            if len(num) >= 7:
                result.append(num)
        return result, "one_col"

def _add_numbers_bulk(svc, numbers):
    added = skipped = 0
    svc = svc.lower().strip()
    if svc not in stock:
        return 0, len(numbers)
    for num in numbers:
        num = re.sub(r"\D", "", str(num))
        if not num:
            skipped += 1; continue
        c_name, _ = get_country_details(num)
        if c_name == "Unknown":
            skipped += 1; continue
        if c_name not in stock[svc]:
            stock[svc][c_name] = []
        stock[svc][c_name].append(num)
        added += 1
    if added:
        save_stock()
    return added, skipped

def _service_select_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("Facebook", "Instagram", "WhatsApp", "Telegram", "Binance", "PC Clone")
    return m

# ── /start handler ────────────────────────────────────────────────────────────

def _extract_username(link):
    if not link:
        return None
    link = link.strip().rstrip("/")
    if "joinchat" in link or "/+" in link:
        return None
    if "t.me/" in link:
        uname = link.split("t.me/")[-1].split("/")[0]
        if uname:
            return "@" + uname
    return None

def _check_member(chat_ref, user_id):
    if not chat_ref:
        return None
    try:
        m = bot.get_chat_member(chat_ref, user_id)
        return m.status not in ("left", "kicked")
    except Exception:
        return None

@bot.message_handler(commands=["start"])
def start_cmd(message):
    u = message.from_user
    register_user(message.chat.id, first_name=u.first_name or "", last_name=u.last_name or "", username=u.username or "")
    uname  = f"@{u.username}" if u.username else (u.first_name or "User")
    uid    = u.id

    # Find any admin's channel2 and group_link to show join buttons
    all_s = get_user_settings(SUPER_ADMIN_ID)
    grp_link = all_s.get("group_link", "")
    ch2      = all_s.get("channel2", "")
    brand    = all_s.get("brand_name", "AR TEAM")

    markup = types.InlineKeyboardMarkup()
    if grp_link:
        markup.add(types.InlineKeyboardButton("🔥 OTP Group JOIN 🔥", url=grp_link))
    if ch2:
        markup.add(types.InlineKeyboardButton("📢 Main Channel JOIN",  url=ch2))
    markup.add(types.InlineKeyboardButton("✅ VERIFY KORO ✅", callback_data="v"))

    bot.send_message(
        message.chat.id,
        f"🔥 <b>{brand}-এ SAGATOM!</b> 🔥\n\n"
        f"╔═════════════════════════════╗\n"
        f"   🧾 <b>USER DASHBOARD</b>\n"
        f"╠═════════════════════════════╣\n"
        f"  👤 <b>User:</b> {uname}\n"
        f"  🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"  📊 <b>Status:</b> 💎 Premium\n"
        f"╚═════════════════════════════╝\n\n"
        f"Nicher channel-e JOIN hoye VERIFY button click koro!",
        reply_markup=markup, parse_mode="HTML",
    )

@bot.message_handler(commands=["test"])
def test_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    otp    = str(random.randint(100000, 999999))
    number = "8801712345678"
    send_otp_message(message.chat.id, otp, number, 12, "Instagram", admin_uid=uid)

@bot.message_handler(commands=["panels"])
def panels_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    panels = get_user_panels(uid)
    if not panels:
        bot.send_message(message.chat.id,
            "📋 Apnar kono panel nei.\n💡 ➕ Add Panel button diye add koro.",
            parse_mode="HTML")
        return
    with _stats_lock:
        stats = {k: dict(v) for k, v in _panel_stats.items() if v.get("owner") == uid}
    lines = "📡 <b>PANEL STATUS</b>\n⚡━━━━━━━━━━━━━━━━⚡\n\n"
    for p in panels:
        pid = p["id"]
        s   = stats.get(pid, {})
        st  = s.get("status", "⏳")
        cnt = s.get("count", 0)
        err = s.get("errors", 0)
        t   = s.get("last")
        last_str = f"{int(time.time() - t)}s ago" if t else "never"
        err_str  = f"  ⚠️ {err} err" if err else ""
        lines += (
            f"{st} <b>{p.get('username', '?')}</b> <code>[{pid}]</code>\n"
            f"   🌐 <code>{p.get('host', '?')}</code>\n"
            f"   📊 {cnt} records  •  🕐 {last_str}{err_str}\n\n"
        )
    lines += f"🔄 <i>Updates every {POLL_INTERVAL}s</i>"
    bot.send_message(message.chat.id, lines, parse_mode="HTML")

@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id,
        "✍️ <b>Broadcast content পাঠাও:</b>\n\n"
        "📝 Text, 🖼️ Photo, 🎥 Video, 🎭 Sticker, 📎 Document — সব accept হবে!",
        parse_mode="HTML")
    bot.register_next_step_handler(msg, do_broadcast)

# ── Callback handler ──────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global stock  # noqa: needed for clr_allok
    uid  = call.from_user.id
    data = call.data
    try:
        # ── Verify join ──────────────────────────────────────────────────────
        if data == "v":
            s        = get_user_settings(SUPER_ADMIN_ID)
            grp_id   = s.get("group_id")
            grp_link = s.get("group_link", "")
            ch2_link = s.get("channel2", "")
            ch2_ref  = _extract_username(ch2_link)
            not_joined = []
            if grp_id and _check_member(grp_id, uid) is False:
                not_joined.append(("🔥 OTP Group", grp_link))
            if ch2_ref and _check_member(ch2_ref, uid) is False:
                not_joined.append(("📢 Main Channel", ch2_link))
            if not_joined:
                bot.answer_callback_query(call.id, "❌ Sob jagay join hao nai!", show_alert=False)
                lines = "❌ <b>Verify hote parcho na!</b>\n\nEkhono join hao nai:\n\n"
                for name, _ in not_joined:
                    lines += f"  🚫 <b>{name}</b>\n"
                err_markup = types.InlineKeyboardMarkup(row_width=1)
                for name, lnk in not_joined:
                    err_markup.add(types.InlineKeyboardButton(f"👉 {name}-e JOIN KORO", url=lnk))
                err_markup.add(types.InlineKeyboardButton("🔄 Verify Koro", callback_data="v"))
                try:
                    bot.edit_message_text(lines, call.message.chat.id, call.message.message_id,
                                          reply_markup=err_markup, parse_mode="HTML")
                except Exception:
                    bot.send_message(call.message.chat.id, lines, reply_markup=err_markup, parse_mode="HTML")
            else:
                bot.delete_message(call.message.chat.id, call.message.message_id)
                vname = call.from_user.first_name or call.from_user.username or "User"
                bot.send_message(call.message.chat.id,
                    f"🔥 <b>VERIFICATION COMPLETE!</b> 🔥\n\n"
                    f"╔═════════════════════════════╗\n"
                    f"   ✅ <b>ACCESS GRANTED</b>\n"
                    f"╠═════════════════════════════╣\n"
                    f"  👋 <b>Welcome, {vname}!</b>\n"
                    f"  🆔 <b>ID:</b> <code>{uid}</code>\n"
                    f"  📊 <b>Status:</b> 💎 Premium\n"
                    f"╚═════════════════════════════╝\n\n"
                    "⚡ <b>Ekkhan number nite parbe!</b> ⚡",
                    reply_markup=main_menu(uid), parse_mode="HTML")

        elif data == "back_to_services":
            show_services(call.message)

        elif data.startswith("s:"):
            svc    = data.split(":")[1]
            markup = types.InlineKeyboardMarkup(row_width=2)
            btns   = []
            if svc in stock:
                for cnt, nums in stock[svc].items():
                    if nums:
                        _, flag = get_country_details(nums[0])
                        btns.append(types.InlineKeyboardButton(f"{flag} {cnt}", callback_data=f"n:{svc}:{cnt}"))
            if btns:
                markup.add(*btns)
            markup.add(types.InlineKeyboardButton("⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_to_services"))
            bot.edit_message_text(f"🔥 <b>{svc.upper()} — COUNTRY</b> 🔥",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="HTML")

        elif data.startswith("n:"):
            _, svc, scnt = data.split(":")
            if scnt in stock.get(svc, {}) and stock[svc][scnt]:
                num = stock[svc][scnt].pop(0)
                save_stock()
                c_name, flag = get_country_details(num)
                # Find which admin owns a panel that has this number's region — just use super admin for now
                admin_uid = SUPER_ADMIN_ID
                register_number(call.message.chat.id, num, admin_uid=admin_uid)
                display_num = num if num.startswith("+") else "+" + num
                s = get_user_settings(admin_uid)
                grp_link = s.get("group_link", "")
                init_kb = types.InlineKeyboardMarkup(row_width=2)
                init_kb.add(
                    types.InlineKeyboardButton("🔄 New Number",     callback_data=f"n:{svc}:{scnt}"),
                    types.InlineKeyboardButton("🌍 Change Country", callback_data=f"s:{svc}"),
                )
                if grp_link:
                    init_kb.add(types.InlineKeyboardButton("📢 OTP Group", url=grp_link))
                bot.edit_message_text(
                    f"✅ <b>Number Assigned!</b>\n\n"
                    f"🔧 <b>Platform:</b> {svc.capitalize()}\n"
                    f"🌍 <b>Country:</b> {flag} {c_name}\n\n"
                    f"📞 <b>Number:</b> <code>{display_num}</code>\n\n"
                    f"⏱ <b>Auto code fetch:</b> 10:00s",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=init_kb, parse_mode="HTML")
                _start_countdown(call.message.chat.id, call.message.message_id,
                                 svc, flag, c_name, display_num, scnt, admin_uid=admin_uid)
            else:
                bot.answer_callback_query(call.id, "⚠️ STOCK SHESH!", show_alert=True)

        # ── Stock clear ──────────────────────────────────────────────────────
        elif data == "clr_menu":
            if not is_admin(uid):
                return
            bot.edit_message_text("🗑️🔥 <b>STOCK CLEAR PANEL</b> 🔥🗑️\n\nKon service clear korbe?",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=_clr_service_markup(), parse_mode="HTML")

        elif data.startswith("clr_s:"):
            if not is_admin(uid):
                return
            svc    = data[6:]
            markup = types.InlineKeyboardMarkup(row_width=1)
            for cnt, nums in stock.get(svc, {}).items():
                if nums:
                    _, flag = get_country_details(nums[0])
                    cb = f"clr_c:{svc}:{cnt}"
                    if len(cb.encode()) <= 64:
                        markup.add(types.InlineKeyboardButton(f"🗑️ {flag} {cnt} ({len(nums)} টি)", callback_data=cb))
            markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="clr_menu"))
            bot.edit_message_text(f"🔥 <b>{svc.upper()} — Kon desh clear korbe?</b>",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="HTML")

        elif data.startswith("clr_c:"):
            if not is_admin(uid):
                return
            _, svc, cnt = data.split(":", 2)
            count = len(stock.get(svc, {}).get(cnt, []))
            _, flag = get_country_details(stock[svc][cnt][0]) if count else ("", "🌐")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Delete Koro", callback_data=f"clr_y:{svc}:{cnt}"),
                types.InlineKeyboardButton("❌ Cancel",      callback_data=f"clr_s:{svc}"),
            )
            bot.edit_message_text(
                f"⚠️ <b>CONFIRM DELETE</b>\n\n"
                f"Service: {svc.upper()}\nCountry: {flag} {cnt}\nNumbers: {count} টি\n\nSure?",
                call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

        elif data.startswith("clr_y:"):
            if not is_admin(uid):
                return
            _, svc, cnt = data.split(":", 2)
            removed = len(stock.get(svc, {}).get(cnt, []))
            if svc in stock and cnt in stock[svc]:
                del stock[svc][cnt]; save_stock()
            bot.edit_message_text(
                f"✅🔥 <b>DELETE COMPLETE!</b>\n\n"
                f"Service: {svc.upper()}\nCountry: {cnt}\nDeleted: {removed} টি",
                call.message.chat.id, call.message.message_id, parse_mode="HTML")

        elif data == "clr_all":
            if not is_admin(uid):
                return
            total = sum(len(n) for d in stock.values() for n in d.values())
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Haa, SOB Clear", callback_data="clr_allok"),
                types.InlineKeyboardButton("❌ Cancel",          callback_data="clr_menu"),
            )
            bot.edit_message_text(f"☠️ <b>CLEAR ALL</b> — Total {total} টি number delete hobe! Sure?",
                                  call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

        elif data == "clr_allok":
            if not is_admin(uid):
                return
            stock = {"whatsapp":{},"facebook":{},"telegram":{},"instagram":{},"pc clone":{},"binance":{}}
            save_stock()
            bot.edit_message_text("🔥 <b>SOB STOCK CLEAR HOYECHE!</b>",
                                  call.message.chat.id, call.message.message_id, parse_mode="HTML")

        # ── Panel remove ─────────────────────────────────────────────────────
        elif data.startswith("rmpanel:"):
            if not is_admin(uid):
                return
            pid    = data.split(":", 1)[1]
            panels = get_user_panels(uid)
            before = len(panels)
            panels = [p for p in panels if p["id"] != pid]
            if len(panels) < before:
                save_user_panels(uid, panels)
                with _stats_lock:
                    _panel_stats.pop(pid, None)
                _dynamic_sessions.pop(pid, None)
                _dynamic_locks.pop(pid, None)
                bot.edit_message_text(f"✅🔥 Panel <code>{pid}</code> removed!",
                                      call.message.chat.id, call.message.message_id, parse_mode="HTML")
            else:
                bot.answer_callback_query(call.id, "❌ Panel pawa jaini!", show_alert=True)

        # ── Service remove ───────────────────────────────────────────────────
        elif data.startswith("rmsvc:"):
            if not is_admin(uid):
                return
            key    = data.split(":", 1)[1]
            svcs   = get_user_services(uid)
            before = len(svcs)
            svcs   = [s for s in svcs if s["key"] != key]
            if len(svcs) < before:
                save_user_services(uid, svcs)
                bot.edit_message_text(f"✅ Service <code>{key}</code> removed!",
                                      call.message.chat.id, call.message.message_id, parse_mode="HTML")
            else:
                bot.answer_callback_query(call.id, "❌ Service pawa jaini!", show_alert=True)

        # ── Admin remove ─────────────────────────────────────────────────────
        elif data.startswith("rmadmin:"):
            if uid != SUPER_ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Only Super Admin remove korte parbe!", show_alert=True)
                return
            target = int(data.split(":")[1])
            if remove_admin(target):
                name = user_names.get(str(target), str(target))
                bot.edit_message_text(f"✅ <b>ADMIN REMOVED!</b>\n\n🗑️ {name} [<code>{target}</code>]",
                                      call.message.chat.id, call.message.message_id, parse_mode="HTML")
                try:
                    bot.send_message(target, "⚠️ আপনার Admin access বাতিল করা হয়েছে!")
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Super Admin remove kora jabe na!", show_alert=True)

        # ── Settings ─────────────────────────────────────────────────────────
        elif data == "set_autodel":
            if not is_admin(uid):
                return
            s = get_user_settings(uid)
            s["auto_delete"] = not s.get("auto_delete", True)
            save_user_settings(uid, s)
            bot.answer_callback_query(call.id, "✅ Auto Delete: " + ("🟢 ON" if s["auto_delete"] else "🔴 OFF"))
            _show_settings_inline(call)

        elif data == "set_grplink":
            if not is_admin(uid):
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id,
                "🔗 <b>OTP Group Link dao:</b>\n<i>Example: https://t.me/mygroup</i>",
                reply_markup=_back_admin_kb(), parse_mode="HTML")
            bot.register_next_step_handler(msg, lambda m: _set_setting_str(m, "group_link"))

        elif data == "set_grpid":
            if not is_admin(uid):
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id,
                "🆔 <b>OTP Group Chat ID dao:</b>\n<i>Example: -1001234567890</i>\n⚠️ Negative number dite hobe",
                reply_markup=_back_admin_kb(), parse_mode="HTML")
            bot.register_next_step_handler(msg, _set_grp_id)

        elif data == "set_brand":
            if not is_admin(uid):
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id,
                "✨ <b>Brand Name dao:</b>\n<i>Example: RABBI TEAM, MY SHOP, XYZ BOT</i>",
                reply_markup=_back_admin_kb(), parse_mode="HTML")
            bot.register_next_step_handler(msg, lambda m: _set_setting_str(m, "brand_name"))

        elif data == "set_channel2":
            if not is_admin(uid):
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id,
                "📢 <b>Main Channel link dao:</b>\n<i>Example: https://t.me/mychannel</i>",
                reply_markup=_back_admin_kb(), parse_mode="HTML")
            bot.register_next_step_handler(msg, lambda m: _set_setting_str(m, "channel2"))

        elif data == "set_botlink":
            if not is_admin(uid):
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id,
                "🤖 <b>Number Bot link dao:</b>\n<i>Example: https://t.me/mybot</i>",
                reply_markup=_back_admin_kb(), parse_mode="HTML")
            bot.register_next_step_handler(msg, lambda m: _set_setting_str(m, "bot_link"))

        # ── Confirm add admin ────────────────────────────────────────────────
        elif data.startswith("confirm_admin:"):
            if uid != SUPER_ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Shudhu Super Admin korte pare!", show_alert=True)
                return
            _, target_str, days_str = data.split(":")
            target_uid = int(target_str)
            days       = int(days_str) if days_str != "0" else None
            if add_admin(target_uid, days=days, added_by=uid):
                exp_str = f"{days} দিন" if days else "Permanent"
                bot.edit_message_text(
                    f"✅🔥 <b>ADMIN ADDED!</b>\n\n"
                    f"👑 <b>User ID:</b> <code>{target_uid}</code>\n"
                    f"⏳ <b>Expiry:</b> {exp_str}\n\n"
                    f"<i>Admin panel access dewa hoyeche.</i>",
                    call.message.chat.id, call.message.message_id, parse_mode="HTML")
                try:
                    bot.send_message(target_uid,
                        f"🎉 <b>আপনাকে Admin করা হয়েছে!</b>\n\n"
                        f"⏳ <b>মেয়াদ:</b> {exp_str}\n\n"
                        f"/start দিয়ে Admin Panel ব্যবহার করুন।",
                        parse_mode="HTML")
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Admin add kora gelo na!", show_alert=True)

        elif data.startswith("cancel_admin:"):
            bot.edit_message_text("❌ <b>Admin add cancel kora hoyeche.</b>",
                                  call.message.chat.id, call.message.message_id, parse_mode="HTML")

    except Exception as e:
        print(f"[CB] Error: {e}")

# ── Settings step handlers ────────────────────────────────────────────────────

def _set_setting_str(message, key):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _go_admin_panel(message); return
    value = (message.text or "").strip()
    if not value:
        msg = bot.send_message(message.chat.id, "❌ Valid value dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, lambda m: _set_setting_str(m, key)); return
    update_user_setting(uid, key, value)
    _go_admin_panel(message, f"✅ <b>Updated!</b>\n\n<b>{key}:</b> {value}")

def _set_grp_id(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _go_admin_panel(message); return
    try:
        gid = int((message.text or "").strip())
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Valid number dao (e.g. -1001234567890):", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _set_grp_id); return
    update_user_setting(uid, "group_id", gid)
    _go_admin_panel(message, f"✅ <b>Group ID set!</b>\n\n<code>{gid}</code>")

# ── Add panel flow ────────────────────────────────────────────────────────────

@bot.message_handler(commands=["addpanel"])
def addpanel_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    _addpanel_state[uid] = {"step": "url", "data": {}}
    msg = bot.send_message(message.chat.id,
        "🔧🔥 <b>ADD NEW PANEL</b> 🔥🔧\n\n"
        "📡 <b>Step 1/3:</b> Panel URL pathao\n"
        "<i>Example: http://1.2.3.4/ints/agent/SMSCDRStats</i>",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _ap_get_url)

def _ap_get_url(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _addpanel_state.pop(uid, None); _go_admin_panel(message); return
    url = (message.text or "").strip()
    base_url = None; panel_type = "smscdr"
    m1 = re.match(r"(https?://[^/]+/(?:ints|sms))(?:/|$)", url)
    m2 = re.match(r"(https?://[^/]+)/agent/(SMSCDRStats|SMSRanges)", url, re.IGNORECASE)
    m3 = re.match(r"(https?://[^/?#]+)/?$", url)
    if m1:
        base_url = m1.group(1); panel_type = "smscdr"
    elif m2:
        base_url = m2.group(1)
        panel_type = "smsranges" if m2.group(2).lower() == "smsranges" else "smscdr"
    elif m3:
        base_url = m3.group(1); panel_type = "smscdr"
    if not base_url:
        msg = bot.send_message(message.chat.id, "❌ Valid URL dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _ap_get_url); return
    host_m = re.search(r"//([^/]+)", base_url)
    _addpanel_state[uid]["data"]["base_url"]   = base_url
    _addpanel_state[uid]["data"]["host"]       = host_m.group(1) if host_m else base_url
    _addpanel_state[uid]["data"]["panel_type"] = panel_type
    type_label = "SMSRanges" if panel_type == "smsranges" else "SMSCDRStats"
    msg = bot.send_message(message.chat.id,
        f"✅ URL: <code>{base_url}</code>\n📊 Type: <b>{type_label}</b>\n\n👤 <b>Step 2/3:</b> Username pathao:",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _ap_get_user)

def _ap_get_user(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _addpanel_state.pop(uid, None); _go_admin_panel(message); return
    username = (message.text or "").strip()
    if not username:
        msg = bot.send_message(message.chat.id, "❌ Username dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _ap_get_user); return
    _addpanel_state[uid]["data"]["username"] = username
    msg = bot.send_message(message.chat.id,
        f"✅ Username: <code>{username}</code>\n\n🔑 <b>Step 3/3:</b> Password pathao:",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _ap_get_pass)

def _ap_get_pass(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _addpanel_state.pop(uid, None); _go_admin_panel(message); return
    password = (message.text or "").strip()
    if not password:
        msg = bot.send_message(message.chat.id, "❌ Password dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _ap_get_pass); return
    data = _addpanel_state.get(uid, {}).get("data", {})
    data["password"] = password
    wait_msg = bot.send_message(message.chat.id, "⏳🔥 <b>Connection test korchi...</b>", parse_mode="HTML")
    panel_id = f"d{int(time.time()) % 100000}"
    panel = {
        "id":         panel_id,
        "host":       data.get("host", ""),
        "base_url":   data.get("base_url", ""),
        "username":   data.get("username", ""),
        "password":   password,
        "panel_type": data.get("panel_type", "smscdr"),
    }
    sess, token = _ints_login(panel)
    try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception:
        pass
    if not sess:
        bot.send_message(message.chat.id,
            "❌ <b>Connection FAILED!</b>\n\nURL, username ba password check koro.",
            parse_mode="HTML")
        _addpanel_state.pop(uid, None); return
    _dynamic_sessions[panel_id] = {"session": sess, "token": token}
    panels = get_user_panels(uid)
    panels.append(panel)
    save_user_panels(uid, panels)
    _start_panel_for_admin(panel, uid)
    bot.send_message(message.chat.id,
        f"✅🔥 <b>PANEL ADDED & STARTED!</b>\n\n"
        f"🆔 <b>ID:</b> <code>{panel_id}</code>\n"
        f"🌐 <b>Host:</b> <code>{data['host']}</code>\n"
        f"👤 <b>User:</b> <code>{data['username']}</code>\n\n"
        f"📡 Monitor started! /panels diye check koro.",
        parse_mode="HTML")
    _addpanel_state.pop(uid, None)

# ── Admin management flows ────────────────────────────────────────────────────

def _show_add_admin(message):
    uid = message.from_user.id
    if uid != SUPER_ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Shudhu Super Admin add korte pare!")
        return
    msg = bot.send_message(message.chat.id,
        "👑 <b>NEW ADMIN ADD</b>\n\n"
        "Notun admin-er Telegram <b>User ID</b> dao:\n"
        "<i>Example: 123456789</i>",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _admin_get_id)

def _admin_get_id(message):
    uid = message.from_user.id
    if _is_back(message.text):
        _go_admin_panel(message); return
    try:
        target_uid = int((message.text or "").strip())
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Valid ID dao (number):", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _admin_get_id); return
    if target_uid == SUPER_ADMIN_ID:
        _go_admin_panel(message, "⚠️ Super Admin already ache!"); return
    # Ask for days
    days_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    days_kb.add("1", "2", "5", "10", "15", "30", "Permanent")
    days_kb.add("🔙 Admin Panel")
    msg = bot.send_message(message.chat.id,
        f"✅ User ID: <code>{target_uid}</code>\n\n"
        "⏳ <b>Koto diner jonno Admin thakbe?</b>\n"
        "Number select koro athoba likhe dao:",
        reply_markup=days_kb, parse_mode="HTML")
    bot.register_next_step_handler(msg, lambda m: _admin_get_days(m, target_uid))

def _admin_get_days(message, target_uid):
    uid = message.from_user.id
    if _is_back(message.text):
        _go_admin_panel(message); return
    txt = (message.text or "").strip().lower()
    if txt in ("permanent", "♾️ permanent", "0"):
        days = None
    else:
        try:
            days = int(txt)
            if days <= 0:
                raise ValueError
        except ValueError:
            msg = bot.send_message(message.chat.id, "❌ Valid number dao (1, 2, 5, 10, 15, 30) athoba Permanent:",
                                   reply_markup=_back_admin_kb())
            bot.register_next_step_handler(msg, lambda m: _admin_get_days(m, target_uid)); return
    exp_str = f"{days} দিন" if days else "Permanent (♾️)"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_admin:{target_uid}:{days or 0}"),
        types.InlineKeyboardButton("❌ Cancel",  callback_data=f"cancel_admin:{target_uid}"),
    )
    bot.send_message(message.chat.id,
        f"🔐 <b>ADMIN ADD CONFIRM</b>\n\n"
        f"👤 <b>User ID:</b> <code>{target_uid}</code>\n"
        f"⏳ <b>Duration:</b> {exp_str}\n\n"
        f"Confirm korte button click koro:",
        reply_markup=main_menu(uid), parse_mode="HTML")
    bot.send_message(message.chat.id, "👆 Confirm koro:", reply_markup=markup)

def _show_remove_admin(message):
    uid      = message.from_user.id
    admins   = _load_admins()
    removable = [(int(k), v) for k, v in admins.items() if int(k) != SUPER_ADMIN_ID]
    if not removable:
        bot.send_message(message.chat.id, "ℹ️ Remove korar moto kono admin nei.", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for aid, info in removable:
        name  = user_names.get(str(aid), str(aid))
        exp   = info.get("expiry")
        if exp:
            remaining = max(0, exp - time.time())
            days_left = int(remaining // 86400)
            exp_tag   = f"⏳ {days_left}d left"
        else:
            exp_tag = "♾️ Permanent"
        markup.add(types.InlineKeyboardButton(
            f"🗑️ {name} [{aid}] — {exp_tag}", callback_data=f"rmadmin:{aid}"))
    bot.send_message(message.chat.id,
        "🗑️ <b>REMOVE ADMIN</b>\n\nKon admin remove korbe?",
        reply_markup=markup, parse_mode="HTML")

# ── Service flows ─────────────────────────────────────────────────────────────

def _svc_get_label(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _addservice_state.pop(uid, None); _go_admin_panel(message); return
    label = (message.text or "").strip()
    if not label:
        msg = bot.send_message(message.chat.id, "❌ Label dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _svc_get_label); return
    _addservice_state[uid]["label"] = label
    msg = bot.send_message(message.chat.id,
        f"✅ Label: <b>{label}</b>\n\n🔑 <b>Step 2/2:</b> Key dao (lowercase):",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _svc_get_key)

def _svc_get_key(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if _is_back(message.text):
        _addservice_state.pop(uid, None); _go_admin_panel(message); return
    key  = (message.text or "").strip().lower()
    svcs = get_user_services(uid)
    if key in [s["key"] for s in svcs]:
        msg = bot.send_message(message.chat.id, f"❌ Key <code>{key}</code> already ache!", reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _svc_get_key); return
    label = _addservice_state.get(uid, {}).get("label", "")
    svcs.append({"label": label, "key": key})
    save_user_services(uid, svcs)
    _addservice_state.pop(uid, None)
    _go_admin_panel(message, f"✅🔥 <b>Service Added!</b>\n\n🏷️ {label}\n🔑 {key}")

# ── Number add flows ──────────────────────────────────────────────────────────

def process_auto_add(message):
    uid = message.from_user.id
    svc = (message.text or "").strip().lower()
    if svc == "❌ cancel":
        _go_admin_panel(message); return
    if svc not in stock:
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("facebook","instagram","whatsapp","telegram","binance","pc clone")
        m.add("❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ <b>Vul service! Abar choose koro:</b>",
                               reply_markup=m, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_auto_add); return
    msg = bot.send_message(message.chat.id,
        f"🔥 <b>{svc.upper()}</b>\n\n📝 <b>Slot name dao:</b>\n<i>Example: Bangladesh 1</i>",
        reply_markup=_cancel_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, svc))

def ask_numbers_for_slot(message, svc):
    slot_name = (message.text or "").strip()
    if slot_name == "❌ Cancel":
        _go_admin_panel(message); return
    if not slot_name:
        msg = bot.send_message(message.chat.id, "❌ Slot name dao:", reply_markup=_cancel_kb())
        bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, svc)); return
    msg = bot.send_message(message.chat.id,
        f"✅ Slot: <b>{slot_name}</b>\n\n📱 <b>{svc.upper()}</b> number pathao:\n"
        f"<i>(Newline ba comma diye alag koro)</i>",
        reply_markup=_cancel_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, lambda m: finalize_auto_add(m, svc, slot_name))

def finalize_auto_add(message, svc, slot_name=None):
    global stock
    uid = message.from_user.id
    if (message.text or "").strip() == "❌ Cancel":
        _go_admin_panel(message); return
    nums = [n.strip() for n in re.split(r"[,\n\r]", message.text) if n.strip()]
    if slot_name:
        if slot_name not in stock[svc]:
            stock[svc][slot_name] = []
        for num in nums:
            stock[svc][slot_name].append(num)
        added_count = len(nums)
    else:
        added_count = 0
        for num in nums:
            c_name, _ = get_country_details(num)
            if c_name == "Unknown":
                continue
            if c_name not in stock[svc]:
                stock[svc][c_name] = []
            stock[svc][c_name].append(num)
            added_count += 1
    save_stock()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Aro Add koro", "🔙 Admin Menu")
    bot.send_message(message.chat.id,
        f"✅🔥 <b>DONE!</b>\n\n🗂 <b>Slot:</b> {slot_name or 'Auto'}\n📱 <b>Added:</b> {added_count} টি",
        reply_markup=markup, parse_mode="HTML")
    bot.register_next_step_handler(
        bot.send_message(message.chat.id, "⬇️ Ki korbe?"),
        lambda m: _after_add_handler(m, svc))

def _after_add_handler(message, last_svc):
    if (message.text or "").strip() == "➕ Aro Add koro":
        msg = bot.send_message(message.chat.id, "📝 <b>Notun slot name dao:</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, last_svc))
    else:
        bot.send_message(message.chat.id, "🔙", reply_markup=main_menu(message.from_user.id))

# ── Excel/document handler ────────────────────────────────────────────────────

@bot.message_handler(content_types=["document"])
def document_handler(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    doc  = message.document
    name = doc.file_name or "file"
    ext  = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ("csv", "xlsx", "xls"):
        bot.send_message(message.chat.id, "⚠️ শুধু CSV, XLSX, XLS file accept হয়।")
        return
    wait = bot.send_message(message.chat.id, "⏳ File processing করছি...")
    try:
        file_info = bot.get_file(doc.file_id)
        raw = bot.download_file(file_info.file_path)
    except Exception as e:
        bot.edit_message_text(f"❌ File download hoyni: {e}", message.chat.id, wait.message_id)
        return
    rows, mode = _parse_spreadsheet(raw, name)
    try:
        bot.delete_message(message.chat.id, wait.message_id)
    except Exception:
        pass
    if mode in ("unknown", "empty") or not rows:
        bot.send_message(message.chat.id,
            "⚠️ <b>File-e kono data paini!</b>\n\n"
            "Format:\n• 2-column: Service | Number\n• 1-column: Number only",
            parse_mode="HTML"); return
    if mode == "two_col":
        svc_map = {}
        for svc, num in rows:
            svc_map.setdefault(svc, []).append(num)
        total_added = total_skipped = 0
        report = ""
        for svc, nums in svc_map.items():
            added, skipped = _add_numbers_bulk(svc, nums)
            total_added += added; total_skipped += skipped
            report += f"{'✅' if added else '⚠️'} <b>{svc.upper()}</b>: +{added}\n"
        bot.send_message(message.chat.id,
            f"📊🔥 <b>EXCEL IMPORT DONE!</b>\n\n{report}\n✅ Total: {total_added}\n⚠️ Skipped: {total_skipped}",
            reply_markup=main_menu(uid), parse_mode="HTML")
    else:
        _pending_excel[uid] = {"numbers": rows, "filename": name}
        msg = bot.send_message(message.chat.id,
            f"📂 <b>FILE LOADED!</b>\n📱 <b>Numbers:</b> {len(rows)}\n\nKon service-e add korbo?",
            reply_markup=_service_select_markup(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _excel_pick_service)

def _excel_pick_service(message):
    uid    = message.from_user.id
    if not is_admin(uid):
        return
    svc_map = {"facebook":"facebook","fb":"facebook","instagram":"instagram","ig":"instagram",
               "whatsapp":"whatsapp","wa":"whatsapp","telegram":"telegram","tg":"telegram",
               "binance":"binance","bnb":"binance","pc clone":"pc clone","pc":"pc clone","clone":"pc clone"}
    svc = svc_map.get((message.text or "").strip().lower())
    if svc is None:
        msg = bot.send_message(message.chat.id, "❌ Valid service choose koro:", reply_markup=_service_select_markup())
        bot.register_next_step_handler(msg, _excel_pick_service); return
    pending = _pending_excel.pop(uid, None)
    if not pending:
        bot.send_message(message.chat.id, "⚠️ Session expired. File abar pathao.", reply_markup=main_menu(uid)); return
    added, skipped = _add_numbers_bulk(svc, pending["numbers"])
    bot.send_message(message.chat.id,
        f"📊🔥 <b>IMPORT DONE!</b>\n\n📎 {pending['filename']}\n💬 {svc.upper()}\n✅ Added: {added}\n⚠️ Skipped: {skipped}",
        reply_markup=main_menu(uid), parse_mode="HTML")

# ── Demo config flows ─────────────────────────────────────────────────────────

def _demo_cfg_number(message):
    if _is_back(message.text):
        _go_admin_panel(message); return
    raw_lines  = re.split(r"[\n,]+", message.text or "")
    candidates = [re.sub(r"\D", "", ln) for ln in raw_lines if re.sub(r"\D", "", ln)]
    valid, invalid = [], []
    for num in candidates:
        if len(num) < 7:
            invalid.append(num); continue
        c_name, _ = get_country_details(num)
        (valid if c_name != "Unknown" else invalid).append(num)
    if not valid:
        msg = bot.send_message(message.chat.id, "❌ Kono valid number paini. Abar dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _demo_cfg_number); return
    with _demo_lock:
        _demo_config["numbers"] = valid
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
    kb.add("4","5","6","7","8"); kb.add("🔙 Admin Panel")
    msg = bot.send_message(message.chat.id, f"✅ {len(valid)} number set!\n\n🔢 OTP digit count:", reply_markup=kb, parse_mode="HTML")
    bot.register_next_step_handler(msg, _demo_cfg_digits)

def _demo_cfg_digits(message):
    if _is_back(message.text):
        _go_admin_panel(message); return
    try:
        d = int(message.text.strip())
        if d < 4 or d > 8:
            raise ValueError
    except ValueError:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
        kb.add("4","5","6","7","8"); kb.add("🔙 Admin Panel")
        msg = bot.send_message(message.chat.id, "❌ 4-8 er modhye dao:", reply_markup=kb)
        bot.register_next_step_handler(msg, _demo_cfg_digits); return
    with _demo_lock:
        _demo_config["digits"] = d
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("Facebook","Instagram","WhatsApp","Telegram","PC Clone"); kb.add("🔙 Admin Panel")
    msg = bot.send_message(message.chat.id, f"✅ Digits: {d}\n\n💬 Service choose koro:", reply_markup=kb, parse_mode="HTML")
    bot.register_next_step_handler(msg, _demo_cfg_service)

def _demo_cfg_service(message):
    if _is_back(message.text):
        _go_admin_panel(message); return
    svc = (message.text or "").strip()
    if not svc:
        msg = bot.send_message(message.chat.id, "❌ Service name dao:")
        bot.register_next_step_handler(msg, _demo_cfg_service); return
    with _demo_lock:
        _demo_config["service"] = svc
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
    kb.add("15","30","60","120","300"); kb.add("🔙 Admin Panel")
    msg = bot.send_message(message.chat.id, f"✅ Service: {svc}\n\n⏱️ Interval (seconds):", reply_markup=kb, parse_mode="HTML")
    bot.register_next_step_handler(msg, _demo_cfg_interval)

def _demo_cfg_interval(message):
    if _is_back(message.text):
        _go_admin_panel(message); return
    try:
        iv = int(message.text.strip())
        if iv < 5:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Minimum 5 second:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _demo_cfg_interval); return
    with _demo_lock:
        _demo_config["interval"] = iv
    bot.send_message(message.chat.id, f"✅ Interval: {iv}s\n\n" + demo_status_text(),
                     reply_markup=demo_menu_markup(), parse_mode="HTML")

# ── Main text handler ─────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def text_handler(message):
    global stock, _demo_active
    uid = message.from_user.id
    txt = message.text or ""
    register_user(message.chat.id)
    svcs = get_user_services(uid) if is_admin(uid) else get_user_services(SUPER_ADMIN_ID)
    svc_map = {s["label"]: s["key"] for s in svcs}

    if txt == "☎️ 𝗡𝗨𝗠𝗕𝗔𝗥 ☎️":
        show_services(message)

    elif txt in svc_map:
        show_countries(message.chat.id, svc_map[txt])

    elif txt == "🔙 Main Menu":
        mname = message.from_user.first_name or message.from_user.username or "User"
        bot.send_message(message.chat.id, f"👋 <b>{mname}</b>, ki korte chao?",
                         reply_markup=main_menu(uid), parse_mode="HTML")

    elif txt == "📞 𝗦𝗔𝗣𝗢𝗥𝗧":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 Support Team", url="https://t.me/Rabbi122q"))
        bot.send_message(message.chat.id,
            "📞 <b>SUPPORT</b>\n⚡━━━━━━━━━━━━━━⚡\n\nKono somossa hole nicher button click koro!",
            reply_markup=markup, parse_mode="HTML")

    elif txt == "📊 𝗦𝗧𝗢𝗖𝗞":
        report = "🔥 <b>LIVE STOCK REPORT</b> 🔥\n⚡━━━━━━━━━━━━⚡\n\n"
        for s, d in stock.items():
            total = sum(len(v) for v in d.values())
            report += f"📱 <b>{s.upper()}</b>: {total} টি\n"
        report += "\n⚡━━━━━━━━━━━━⚡"
        bot.send_message(message.chat.id, report, parse_mode="HTML")

    elif txt == "⚙️ 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 ⚙️" and is_admin(uid):
        _go_admin_panel(message)

    elif txt == "🔥📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁" and is_admin(uid):
        msg = bot.send_message(message.chat.id,
            "✍️ <b>Broadcast content পাঠাও:</b>", reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, do_broadcast)

    elif txt == "⚡👥 𝗨𝘀𝗲𝗿 𝗖𝗼𝘂𝗻𝘁" and is_admin(uid):
        bot.send_message(message.chat.id, f"👥 <b>TOTAL USERS:</b> {len(users)} জন", parse_mode="HTML")

    elif txt == "📋👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁" and is_admin(uid):
        total  = len(users)
        PAGE   = 50
        chunks = [users[i:i+PAGE] for i in range(0, total, PAGE)]
        for idx, chunk in enumerate(chunks):
            lines = f"📋 <b>USER LIST</b> — Total: <b>{total}</b>"
            if len(chunks) > 1:
                lines += f" | Page {idx+1}/{len(chunks)}"
            lines += "\n\n"
            for i, user_id in enumerate(chunk, start=idx*PAGE+1):
                name = user_names.get(str(user_id), "—")
                lines += f"{i}. 🆔 <code>{user_id}</code>  👤 {name}\n"
            bot.send_message(message.chat.id, lines, parse_mode="HTML")

    elif txt == "➕ 𝗡𝘂𝗺𝗯𝗮𝗿 𝗔𝗱𝗱" and is_admin(uid):
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("facebook","instagram","whatsapp","telegram","binance","pc clone")
        m.add("❌ Cancel")
        msg = bot.send_message(message.chat.id, "🔥 <b>Service choose koro:</b>",
                               reply_markup=m, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_auto_add)

    elif txt == "🗑️ 𝗦𝗼𝗯 𝗖𝗹𝗲𝗮𝗿" and is_admin(uid):
        bot.send_message(message.chat.id, "🗑️🔥 <b>STOCK CLEAR PANEL</b>\n\nKon service clear korbe?",
                         reply_markup=_clr_service_markup(), parse_mode="HTML")

    elif txt == "🎭 𝗗𝗘𝗠𝗢 𝗢𝗧𝗣" and is_admin(uid):
        bot.send_message(message.chat.id, demo_status_text(), reply_markup=demo_menu_markup(), parse_mode="HTML")

    elif txt == "▶️ 𝗗𝗘𝗠𝗢 𝗦𝗧𝗔𝗥𝗧" and is_admin(uid):
        with _demo_lock:
            _demo_active = True
        bot.send_message(message.chat.id, "🟢🔥 <b>DEMO OTP STARTED!</b>", reply_markup=demo_menu_markup(), parse_mode="HTML")

    elif txt == "⏹️ 𝗗𝗘𝗠𝗢 𝗦𝗧𝗢𝗣" and is_admin(uid):
        with _demo_lock:
            _demo_active = False
        bot.send_message(message.chat.id, "🔴 <b>DEMO OTP STOPPED!</b>", reply_markup=demo_menu_markup(), parse_mode="HTML")

    elif txt == "⚙️ 𝗗𝗘𝗠𝗢 𝗖𝗢𝗡𝗙𝗜𝗚" and is_admin(uid):
        msg = bot.send_message(message.chat.id,
            "📱 <b>Phone number(s) dao:</b>\n<i>(Newline ba comma diye alag koro)</i>",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _demo_cfg_number)

    elif txt == "📊 𝗣𝗮𝗻𝗲𝗹𝘀" and is_admin(uid):
        panels_cmd(message)

    elif txt == "👑 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻" and is_admin(uid):
        _show_add_admin(message)

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻" and is_admin(uid):
        _show_remove_admin(message)

    elif txt == "➕ 𝗔𝗱𝗱 𝗣𝗮𝗻𝗲𝗹" and is_admin(uid):
        _addpanel_state[uid] = {"step": "url", "data": {}}
        msg = bot.send_message(message.chat.id,
            "🔧🔥 <b>ADD NEW PANEL</b>\n\n📡 <b>Step 1/3:</b> Panel URL pathao",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _ap_get_url)

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗮𝗻𝗲𝗹" and is_admin(uid):
        panels = get_user_panels(uid)
        if not panels:
            bot.send_message(message.chat.id, "📋 Kono panel nei. ➕ Add Panel diye add koro.")
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p in panels:
                pid = p["id"]
                with _stats_lock:
                    s = _panel_stats.get(pid, {})
                st = s.get("status", "⏳")
                markup.add(types.InlineKeyboardButton(
                    f"{st} {p.get('username','?')} — {p.get('host','?')}", callback_data=f"rmpanel:{pid}"))
            bot.send_message(message.chat.id, "🗑️🔥 <b>REMOVE PANEL</b>\n\nKon panel remove korbe?",
                             reply_markup=markup, parse_mode="HTML")

    elif txt == "➕ 𝗔𝗱𝗱 𝗦𝗲𝗿𝘃𝗶𝗰𝗲" and is_admin(uid):
        _addservice_state[uid] = {}
        msg = bot.send_message(message.chat.id,
            "📋🔥 <b>ADD SERVICE</b>\n\n🏷️ <b>Step 1/2:</b> Button label dao:",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _svc_get_label)

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗦𝗲𝗿𝘃𝗶𝗰𝗲" and is_admin(uid):
        svcs = get_user_services(uid)
        if not svcs:
            bot.send_message(message.chat.id, "📋 Kono service nei!")
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for s in svcs:
                markup.add(types.InlineKeyboardButton(f"🗑️ {s['label']} [{s['key']}]", callback_data=f"rmsvc:{s['key']}"))
            bot.send_message(message.chat.id, "🗑️ <b>REMOVE SERVICE</b>", reply_markup=markup, parse_mode="HTML")

    elif txt == "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀" and is_admin(uid):
        _show_settings(message)

    elif txt in ("🔙 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟", "🔙 Admin Panel") and is_admin(uid):
        _go_admin_panel(message)

    elif txt == "⬅️🔙 𝗨𝘀𝗲𝗿 𝗠𝗲𝗻𝘂":
        mname = message.from_user.first_name or "User"
        bot.send_message(message.chat.id, f"👋 <b>{mname}</b>", reply_markup=main_menu(uid), parse_mode="HTML")

    elif txt == "➕ Aro Add koro" and is_admin(uid):
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("facebook","instagram","whatsapp","telegram","binance","pc clone")
        m.add("❌ Cancel")
        msg = bot.send_message(message.chat.id, "🔥 <b>Service choose koro:</b>", reply_markup=m, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_auto_add)

# ── Startup ───────────────────────────────────────────────────────────────────

try:
    requests.get(
        f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook?drop_pending_updates=true",
        timeout=10)
    print("[START] Webhook cleared.")
except Exception as e:
    print(f"[START] Webhook clear failed: {e}")

time.sleep(2)

# Start auto-expire thread
threading.Thread(target=auto_expire_admins, daemon=True).start()
threading.Thread(target=demo_monitor, daemon=True).start()

# Load all admins' panels and start monitors
all_panels_data = load_json(USER_PANELS_FILE, {})
for admin_uid_str, panels in all_panels_data.items():
    admin_uid_int = int(admin_uid_str)
    for panel in panels:
        try:
            _start_panel_for_admin(panel, admin_uid_int)
            print(f"[DYN] Loaded panel: {panel['id']} for admin={admin_uid_int}")
        except Exception as e:
            print(f"[DYN] Error loading panel: {e}")

print("🔥 AR OTP BOT is running! 🔥")
print(f"   ▸ Super Admin: {SUPER_ADMIN_ID}")
print(f"   ▸ Poll Interval: {POLL_INTERVAL}s")

def _clear_webhook():
    try:
        requests.get(
            f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10)
    except Exception:
        pass

while True:
    try:
        _clear_webhook()
        time.sleep(1)
        print("[POLLING] Starting infinity_polling...")
        bot.infinity_polling(
            timeout=20,
            long_polling_timeout=15,
            allowed_updates=["message", "callback_query"],
        )
        print("[POLLING] Stopped, restarting...")
    except requests.exceptions.ReadTimeout:
        print("[POLLING] ReadTimeout — restarting in 3s...")
        time.sleep(3)
    except requests.exceptions.ConnectionError:
        print("[POLLING] ConnectionError — restarting in 5s...")
        time.sleep(5)
    except Exception as e:
        print(f"[POLLING] Error: {type(e).__name__}: {e} — restarting in 5s...")
        time.sleep(5)
