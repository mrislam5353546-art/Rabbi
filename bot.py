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
import tempfile
import openpyxl
import xlrd
from bs4 import BeautifulSoup
from phonenumbers import region_code_for_number, geocoder

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
ADMIN_IDS = [8523774444]
CHANNEL_2 = "https://t.me/mailbotnewsofficial"

# ── Panel 1 (Mahofuza) ───────────────────────────────────────────────────────
P1_BASE_URL = "http://91.232.105.47/ints"
P1_LOGIN_PAGE = P1_BASE_URL + "/login"
P1_SIGNIN_URL = P1_BASE_URL + "/signin"
P1_CDR_PAGE = P1_BASE_URL + "/agent/SMSCDRStats"
P1_CDR_DATA_URL = P1_BASE_URL + "/agent/res/data_smscdr.php"
P1_USER_NAME = "Mahofuza"
P1_PASSWORD = "Mahofuza"

# ── Panel 2 (Sagardas50 / XISORA) ────────────────────────────────────────────
P2_BASE_URL = "http://94.23.31.29/sms"
P2_SIGNIN_URL = P2_BASE_URL + "/signmein"
P2_REPORTS_PAGE = P2_BASE_URL + "/client/Reports"
P2_DATA_URL = P2_BASE_URL + "/client/ajax/dt_reports.php"
P2_USER_NAME = "Sagardas50"
P2_PASSWORD = "Sagardas50"

# ── Panel 3 (Rabbi1_FD) ───────────────────────────────────────────────────────
P3_BASE_URL = "http://168.119.13.175/ints"
P3_LOGIN_PAGE = P3_BASE_URL + "/login"
P3_SIGNIN_URL = P3_BASE_URL + "/signin"
P3_CDR_PAGE = P3_BASE_URL + "/agent/SMSCDRStats"
P3_CDR_DATA_URL = P3_BASE_URL + "/agent/res/data_smscdr.php"
P3_USER_NAME = "Rabbi1_FD"
P3_PASSWORD = "Rabbi1_FD"

# ── Panel 4 (Rabbi12) ─────────────────────────────────────────────────────────
P4_BASE_URL = "http://144.217.71.192/ints"
P4_LOGIN_PAGE = P4_BASE_URL + "/login"
P4_SIGNIN_URL = P4_BASE_URL + "/signin"
P4_CDR_PAGE = P4_BASE_URL + "/agent/SMSCDRStats"
P4_CDR_DATA_URL = P4_BASE_URL + "/agent/res/data_smscdr.php"
P4_USER_NAME = "Rabbi12"
P4_PASSWORD = "Rabbi12"

# ── Panel 5 (Rabbi12_v2 / 51.75.144.178) ─────────────────────────────────────
P5_BASE_URL = "http://51.75.144.178/ints"
P5_LOGIN_PAGE = P5_BASE_URL + "/login"
P5_SIGNIN_URL = P5_BASE_URL + "/signin"
P5_CDR_PAGE = P5_BASE_URL + "/agent/SMSCDRStats"
P5_CDR_DATA_URL = P5_BASE_URL + "/agent/res/data_smscdr.php"
P5_USER_NAME = "Rabbi12"
P5_PASSWORD = "Rabbi12@"

# ── Panel 6 (Sagardas50 / TrueSMS.net — SMSRanges) ───────────────────────────
P6_BASE_URL = "https://truesms.net"
P6_LOGIN_PAGE = P6_BASE_URL + "/login"
P6_SIGNIN_URL = P6_BASE_URL + "/signin"
P6_CDR_PAGE = P6_BASE_URL + "/agent/SMSRanges"
P6_CDR_DATA_URL = P6_BASE_URL + "/agent/res/data_smsranges.php"
P6_USER_NAME = "Sagardas50"
P6_PASSWORD = "Sagardas50"


POLL_INTERVAL = 8
DATA_FILE = "stock_data.json"
USERS_FILE = "users.json"
SEEN_FILE = "seen_otps.json"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=40)

# ── Persistent helpers ────────────────────────────────────────────────────────


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


stock = load_json(
    DATA_FILE,
    {
        "whatsapp": {},
        "facebook": {},
        "telegram": {},
        "instagram": {},
        "pc clone": {},
        "binance": {},
    },
)
users = load_json(USERS_FILE, [])
seen_otps = load_json(SEEN_FILE, {})
USER_NAMES_FILE = "user_names.json"
user_names = load_json(USER_NAMES_FILE, {})

SUPER_ADMIN_ID = 8523774444
ADMINS_FILE = "admins.json"
_extra_admins = load_json(ADMINS_FILE, [])
for _aid in _extra_admins:
    if _aid not in ADMIN_IDS:
        ADMIN_IDS.append(_aid)


def save_admins():
    save_json(ADMINS_FILE, [a for a in ADMIN_IDS if a != SUPER_ADMIN_ID])


def add_admin(uid):
    if uid not in ADMIN_IDS:
        ADMIN_IDS.append(uid)
        save_admins()
        return True
    return False


def remove_admin(uid):
    if uid == SUPER_ADMIN_ID:
        return False
    if uid in ADMIN_IDS:
        ADMIN_IDS.remove(uid)
        save_admins()
        return True
    return False

GROUP_SETTINGS_FILE = "group_settings.json"
_group_settings = load_json(GROUP_SETTINGS_FILE, {
    "otp_group_id": -1003738666960,
    "otp_group_link": "https://t.me/aR_OTP_rcv",
    "auto_delete": True,
    "auto_delete_seconds": 3600,
    "channel2": "https://t.me/mailbotnewsofficial",
    "bot_link": "https://t.me/ar_otp_bot",
})

CHANNEL_1 = _group_settings["otp_group_link"]
OTP_GROUP_ID = _group_settings["otp_group_id"]


def save_group_settings():
    save_json(GROUP_SETTINGS_FILE, _group_settings)


def get_otp_group_id():
    return _group_settings.get("otp_group_id")


def get_otp_group_link():
    return _group_settings.get("otp_group_link", "")


def _extract_username(link):
    """Extract @username from a t.me link for use with get_chat_member."""
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
    """Returns True if member, False if not, None if cannot check."""
    if not chat_ref:
        return None
    try:
        m = bot.get_chat_member(chat_ref, user_id)
        return m.status not in ("left", "kicked")
    except Exception:
        return None


def get_channel2():
    return _group_settings.get("channel2", "https://t.me/mailbotnewsofficial")


def get_bot_link():
    return _group_settings.get("bot_link", "https://t.me/ar_otp_bot")


def is_auto_delete():
    return _group_settings.get("auto_delete", True)


def _schedule_delete(chat_id, msg_id):
    delay = _group_settings.get("auto_delete_seconds", 3600)
    def _do_delete():
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    threading.Timer(delay, _do_delete).start()

# ── Message templates ──────────────────────────────────────────────────────────

TEMPLATES_FILE = "message_templates.json"
_DEFAULT_TEMPLATES = {
    "start": (
        "🔥 <b>𝗔𝗥 𝗢𝗧𝗣 𝗕𝗢𝗧-𝗲 𝗦𝗔𝗚𝗢𝗧𝗢𝗠!</b> 🔥\n\n"
        "╔═════════════════════════════╗\n"
        "   🧾 <b>USER DASHBOARD</b>\n"
        "╠═════════════════════════════╣\n"
        "  👤 <b>User:</b> {uname}\n"
        "  🆔 <b>ID:</b> <code>{uid}</code>\n"
        "  📊 <b>Status:</b> 💎 Premium\n"
        "  🚀 <b>Workers:</b> 0\n"
        "╚═════════════════════════════╝\n\n"
        "╔══════════════════╗\n"
        " 𝗡𝗶𝗰𝗵𝗲𝗿 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝗲 <b>𝗝𝗢𝗜𝗡</b> 𝗵𝗼𝘆𝗲\n"
        " <b>𝗩𝗘𝗥𝗜𝗙𝗬</b> 𝗯𝗮𝘁𝗮𝗻𝗲 𝗰𝗹𝗶𝗰𝗸 𝗸𝗼𝗿𝗼!\n"
        "╚══════════════════╝\n\n"
        "🤖 <i>𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝙗𝙮</i>  <b>𝗔𝗥 𝗢𝗧𝗣 𝗕𝗢𝗧</b>"
    ),
    "otp_group": (
        "🌟══════════════🌟\n"
        "✨ <b>Messga OTP Received</b> ✨\n\n"
        "⚙ <b>Service:</b> {svc}\n"
        "☎ <b>Number:</b> <code>{number}</code>\n"
        "🌍 <b>Country:</b> {country} {flag}\n\n"
        "📲 <b>OTP Code:</b> <code>{otp}</code>\n\n"
        "🌟══════════════🌟\n\n"
        "🌟 <i>𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝙗𝙮</i>  <b>🅐🅡 🆃🅴🅰🅼</b> 🌟"
    ),
    "otp_dm": (
        "🌟══════════════🌟\n"
        "✨ <b>Messga OTP Received</b> ✨\n\n"
        "⚙ <b>Service:</b> {svc}\n"
        "☎ <b>Number:</b> <code>{number}</code>\n"
        "🌍 <b>Country:</b> {country} {flag}\n\n"
        "📲 <b>OTP Code:</b> <code>{otp}</code>\n\n"
        "🌟══════════════🌟\n\n"
        "🌟 <i>𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝙗𝙮</i>  <b>🅐🅡 🆃🅴🅰🅼</b> 🌟"
    ),
    "verify_success": (
        "🔥 <b>VERIFICATION COMPLETE!</b> 🔥\n\n"
        "╔═════════════════════════════╗\n"
        "   ✅ <b>ACCESS GRANTED</b>\n"
        "╠═════════════════════════════╣\n"
        "  👋 <b>Welcome, {vname}!</b>\n"
        "  🆔 <b>ID:</b> <code>{uid}</code>\n"
        "  📊 <b>Status:</b> 💎 Premium\n"
        "╚═════════════════════════════╝\n\n"
        "⚡ <b>𝗘𝗸𝗸𝗵𝗼𝗻 𝗻𝘂𝗺𝗯𝗮𝗿 𝗻𝗶𝘁𝗲 𝗽𝗮𝗿𝗯𝗲!</b> ⚡"
    ),
    "number_assigned": (
        "✅ <b>Number Assigned Successfully !</b>\n\n"
        "🔧 <b>Platform :</b> {svc}\n"
        "🌍 <b>Country :</b> {flag} {country}\n\n"
        "📞 <b>Number :</b> <code>{number}</code>\n\n"
        "⏱ <b>Auto code fetch :</b> 10:00s"
    ),
}
_templates = load_json(TEMPLATES_FILE, dict(_DEFAULT_TEMPLATES))
for _k, _v in _DEFAULT_TEMPLATES.items():
    if _k not in _templates:
        _templates[_k] = _v
_edit_template_state = {}


def save_templates():
    save_json(TEMPLATES_FILE, _templates)


def get_template(key):
    return _templates.get(key, _DEFAULT_TEMPLATES.get(key, ""))


_TEMPLATE_LABELS = {
    "start": "🚀 Start / Welcome মেসেজ",
    "otp_group": "📲 OTP মেসেজ (Group)",
    "otp_dm": "📲 OTP মেসেজ (DM/User)",
    "verify_success": "✅ Verify Success মেসেজ",
    "number_assigned": "☎️ Number Assigned মেসেজ",
}

_TEMPLATE_VARS = {
    "start": "{uname} = ইউজার নাম, {uid} = ইউজার আইডি",
    "otp_group": "{svc} = সার্ভিস, {number} = নম্বর, {country} = দেশ, {flag} = ফ্ল্যাগ, {otp} = OTP কোড",
    "otp_dm": "{svc} = সার্ভিস, {number} = নম্বর, {country} = দেশ, {flag} = ফ্ল্যাগ, {otp} = OTP কোড",
    "verify_success": "{vname} = ইউজার নাম, {uid} = ইউজার আইডি",
    "number_assigned": "{svc} = সার্ভিস, {country} = দেশ, {flag} = ফ্ল্যাগ, {number} = নম্বর",
}

# ── End Message templates ──────────────────────────────────────────────────────

SERVICES_FILE = "services.json"
_DEFAULT_SERVICES = [
    {"label": "Instagram →", "key": "instagram"},
    {"label": "Facebook 💎", "key": "facebook"},
    {"label": "WhatsApp", "key": "whatsapp"},
    {"label": "PC Clone 💎", "key": "pc clone"},
]
_services = load_json(SERVICES_FILE, list(_DEFAULT_SERVICES))
_addservice_state = {}
_countdowns = {}

user_map = {}
user_map_lock = threading.Lock()
assigned_time = {}


def register_number(user_id, number):
    clean = re.sub(r"\D", "", str(number))
    with user_map_lock:
        user_map[clean] = user_id
        assigned_time[clean] = time.time()


def mask_number(number):
    s = str(number)
    if len(s) <= 9:
        return s[:3] + "***" + s[-3:]
    return s[:6] + "***" + s[-3:]


# ── OTP Messages ──────────────────────────────────────────────────────────────


def send_otp_message(chat_id, otp, number, seconds, service=""):
    svc = service.upper() if service else "—"
    c_name, flag = get_country_details(number)
    if chat_id == get_otp_group_id():
        message = get_template("otp_group").format(
            svc=svc, number=mask_number(number), country=c_name, flag=flag, otp=otp
        )
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🤖 𝗡𝘂𝗺𝗯𝗲𝗿 𝗕𝗼𝘁", url=get_bot_link()),
            types.InlineKeyboardButton("📢 𝗠𝗮𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", url=get_channel2()),
        )
        try:
            sent = bot.send_message(
                chat_id=chat_id, text=message, parse_mode="HTML", reply_markup=markup
            )
            if is_auto_delete():
                _schedule_delete(chat_id, sent.message_id)
        except Exception as e:
            print(f"[MONITOR] Group send error: {e}")
    else:
        message = get_template("otp_dm").format(
            svc=svc, number=mask_number(number), country=c_name, flag=flag, otp=otp
        )
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
        except Exception as e:
            print(f"[MONITOR] User send error to {chat_id}: {e}")


def _dispatch_otp(otp, number, seconds, service=""):
    send_otp_message(get_otp_group_id(), otp, number, seconds, service)
    clean = re.sub(r"\D", "", str(number))
    with user_map_lock:
        uid = user_map.pop(clean, None)
        assigned_time.pop(clean, None)
    if uid:
        send_otp_message(uid, otp, number, seconds, service)


def send_status_message(chat_id, status_text):
    message = (
        "⚙️ <b>𝗦𝗧𝗔𝗧𝗨𝗦 𝗔𝗟𝗘𝗥𝗧</b> ⚙️\n"
        "🔥━━━━━━━━━━━━━━🔥\n\n"
        f"📛 {status_text} 📛\n\n"
        "🔥━━━━━━━━━━━━━━🔥\n"
        "🤖⚡ <b>RABBI 𝗢𝗧𝗣 𝗕𝗢𝗧 — 𝗔𝗖𝗧𝗜𝗩𝗘</b> ⚡🤖"
    )
    try:
        bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
    except Exception as e:
        print(f"[MONITOR] Status send error: {e}")


# ── Country helpers ───────────────────────────────────────────────────────────


def get_country_details(num_str):
    try:
        num_str = str(num_str).strip()
        if not num_str.startswith("+"):
            num_str = "+" + num_str
        parsed = phonenumbers.parse(num_str)
        country_code = region_code_for_number(parsed)
        country_name = geocoder.description_for_number(parsed, "en")
        flag = "".join(chr(ord(c.upper()) + 127397) for c in country_code)
        return country_name, flag
    except Exception:
        return "Unknown", "🌐"


# ── Stock helpers ─────────────────────────────────────────────────────────────


def save_stock():
    save_json(DATA_FILE, stock)


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


# ── Panel sessions ────────────────────────────────────────────────────────────

_p1_session = None
_p1_sesskey = None
_p1_lock = threading.Lock()

_p2_session = None
_p2_lock = threading.Lock()

_p3_session = None
_p3_csstr = None
_p3_lock = threading.Lock()

_p4_session = None
_p4_sesskey = None
_p4_lock = threading.Lock()

_p5_session = None
_p5_sesskey = None
_p5_lock = threading.Lock()

_p6_session = None
_p6_sesskey = None
_p6_lock = threading.Lock()


# ── Panel stats (for /panels command) ─────────────────────────────────────────
_panel_stats = {
    "p1": {
        "name": "Mahofuza",
        "host": "91.232.105.47",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
    "p2": {
        "name": "Sagardas50",
        "host": "94.23.31.29",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
    "p3": {
        "name": "Rabbi1_FD",
        "host": "168.119.13.175",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
    "p4": {
        "name": "Rabbi12",
        "host": "144.217.71.192",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
    "p5": {
        "name": "Rabbi12_v2",
        "host": "51.75.144.178",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
    "p6": {
        "name": "TrueSMS/Ranges",
        "host": "truesms.net",
        "status": "⏳",
        "count": 0,
        "last": None,
        "errors": 0,
    },
}
_stats_lock = threading.Lock()


def _record_fetch(pid, count):
    with _stats_lock:
        _panel_stats[pid]["status"] = "🟢"
        _panel_stats[pid]["count"] = count
        _panel_stats[pid]["last"] = time.time()
        _panel_stats[pid]["errors"] = 0


def _record_error(pid):
    with _stats_lock:
        _panel_stats[pid]["status"] = "🔴"
        _panel_stats[pid]["errors"] += 1


# ── Demo OTP state ─────────────────────────────────────────────────────────────
_demo_active = False
_demo_lock = threading.Lock()
_demo_cfg_id_counter = 1
_demo_configs: list = [
    {"id": 1, "name": "Config 1", "active": False, "numbers": ["8801700000000"], "digits": 6, "services": ["Facebook"], "interval": 30}
]
_demo_next_fire: dict = {}
_demo_svc_state: dict = {}
_demo_cfg_temp: dict = {}

seen_lock = threading.Lock()

# ── Dynamic panel system ───────────────────────────────────────────────────────
DYNAMIC_PANELS_FILE = "dynamic_panels.json"
_dynamic_panels = load_json(DYNAMIC_PANELS_FILE, [])
_dynamic_sessions = {}
_dynamic_locks = {}
_addpanel_state = {}
_pending_excel = {}  # uid → {'numbers': [...], 'filename': str}


def save_dynamic_panels():
    save_json(DYNAMIC_PANELS_FILE, _dynamic_panels)


def _get_dp_lock(pid):
    if pid not in _dynamic_locks:
        _dynamic_locks[pid] = threading.Lock()
    return _dynamic_locks[pid]


def _ints_login(panel):
    pid = panel["id"]
    base = panel["base_url"]
    panel_type = panel.get("panel_type", "smscdr")
    cdr_endpoint = "/agent/SMSRanges" if panel_type == "smsranges" else "/agent/SMSCDRStats"
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(base + "/login", timeout=15, verify=False)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if m:
            answer = int(m.group(1)) + int(m.group(2))
            r2 = sess.post(
                base + "/signin",
                data={
                    "username": panel["username"],
                    "password": panel["password"],
                    "capt": answer,
                },
                timeout=15,
                allow_redirects=True,
                verify=False,
            )
        else:
            r2 = sess.post(
                base + "/signin",
                data={"username": panel["username"], "password": panel["password"]},
                timeout=15,
                allow_redirects=True,
                verify=False,
            )
        if "login" in r2.url.lower() and "agent" not in r2.url.lower():
            print(f"[{pid}] Login failed: {r2.url}")
            return None, None
        cdr_page = base + cdr_endpoint
        r3 = sess.get(cdr_page, timeout=15, headers={"Referer": base + "/agent/"}, verify=False)
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        cs = re.search(r"csstr=([a-f0-9]+)", r3.text)
        token = sk.group(1) if sk else (cs.group(1) if cs else "")
        print(f"[{pid}] Logged in. token={token[:10] if token else 'none'}...")
        return sess, token
    except Exception as e:
        print(f"[{pid}] Login error: {e}")
        return None, None


def _ints_fetch(panel):
    pid = panel["id"]
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
        sess = sd["session"]
        token = sd.get("token", "")
        today = time.strftime("%Y-%m-%d")

        def build_url():
            return (
                f"{data_url}"
                f"?fdate1={today}%2000:00:00&fdate2={today}%2023:59:59"
                f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                f"&sesskey={token}"
            )

        headers = {"Referer": cdr_page, "X-Requested-With": "XMLHttpRequest"}
        try:
            r = sess.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[{pid}] Bad response, re-logging in.")
                _dynamic_sessions[pid] = {}
                s, tok = _ints_login(panel)
                if not s:
                    _record_error(pid)
                    return found
                _dynamic_sessions[pid] = {"session": s, "token": tok}
                r = s.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch(pid, len(rows))
            if found:
                print(f"[{pid}] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[{pid}] Fetch error: {e}")
            _record_error(pid)
            _dynamic_sessions[pid] = {}
    return found


def _start_dynamic_panel(panel):
    pid = panel["id"]
    with _stats_lock:
        _panel_stats[pid] = {
            "name": panel.get("username", pid),
            "host": panel.get("host", ""),
            "status": "⏳",
            "count": 0,
            "last": None,
            "errors": 0,
        }

    def monitor():
        global seen_otps
        print(f"[{pid}-MONITOR] Started. Pre-loading existing records...")
        existing = _ints_fetch(panel)
        with seen_lock:
            for key in existing:
                seen_otps[key] = True
            save_json(SEEN_FILE, seen_otps)
        print(
            f"[{pid}-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones..."
        )
        while True:
            try:
                process_new_otps(_ints_fetch(panel))
            except Exception as e:
                print(f"[{pid}-MONITOR] Loop error: {e}")
            time.sleep(POLL_INTERVAL)

    threading.Thread(target=monitor, daemon=True).start()


def extract_otp_from_sms(sms_text):
    cleaned = re.sub(r"(?<=\d) (?=\d)", "", sms_text)
    m = re.search(r"\b(\d{4,8})\b", cleaned)
    return m.group(1) if m else None


# ── Panel 1 login & fetch (Mahofuza) ─────────────────────────────────────────


def p1_login():
    global _p1_session, _p1_sesskey
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(P1_LOGIN_PAGE, timeout=15)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if not m:
            print("[P1] Could not find captcha")
            return False
        answer = int(m.group(1)) + int(m.group(2))
        r2 = sess.post(
            P1_SIGNIN_URL,
            data={"username": P1_USER_NAME, "password": P1_PASSWORD, "capt": answer},
            timeout=15,
            allow_redirects=True,
        )
        if "login" in r2.url.lower() or "login" in r2.text.lower()[:500]:
            print("[P1] Login failed — still on login page")
            return False
        r3 = sess.get(
            P1_CDR_PAGE, timeout=15, headers={"Referer": P1_BASE_URL + "/agent/"}
        )
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        _p1_sesskey = sk.group(1) if sk else ""
        _p1_session = sess
        print(f"[P1] Logged in. sesskey={_p1_sesskey}")
        return True
    except Exception as e:
        print(f"[P1] Login error: {e}")
        return False


def fetch_panel1():
    global _p1_session, _p1_sesskey
    found = {}
    with _p1_lock:
        try:
            today = time.strftime("%Y-%m-%d")

            def build_url():
                return (
                    f"{P1_CDR_DATA_URL}"
                    f"?fdate1={today}%2000:00:00"
                    f"&fdate2={today}%2023:59:59"
                    f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                    f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                    f"&sesskey={_p1_sesskey or ''}"
                )

            headers = {"Referer": P1_CDR_PAGE, "X-Requested-With": "XMLHttpRequest"}
            if _p1_session is None:
                if not p1_login():
                    return found
            r = _p1_session.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[P1] Bad response ({r.status_code}), re-logging in.")
                _p1_session = None
                if not p1_login():
                    return found
                r = _p1_session.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p1", len(rows))
            if found:
                print(f"[P1] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P1] Fetch error: {e}")
            _record_error("p1")
            _p1_session = None
    return found


# ── Panel 2 login & fetch (Sagardas50 / XISORA) ──────────────────────────────


def p2_login():
    global _p2_session
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.post(
            P2_SIGNIN_URL,
            data={"username": P2_USER_NAME, "password": P2_PASSWORD},
            timeout=15,
            allow_redirects=True,
        )
        if "signin" in r.url.lower() or "login" in r.url.lower():
            print("[P2] Login failed — still on login page")
            return False
        _p2_session = sess
        print(f"[P2] Logged in. URL={r.url}")
        return True
    except Exception as e:
        print(f"[P2] Login error: {e}")
        return False


def fetch_panel2():
    global _p2_session
    found = {}
    with _p2_lock:
        try:
            today = time.strftime("%Y-%m-%d")
            url = (
                f"{P2_DATA_URL}"
                f"?fdate1={today}%2000:00:00"
                f"&fdate2={today}%2023:59:59"
                f"&ftermination=&fclient=&fnum=&fcli="
                f"&fgdate=0&fgtermination=0&fgclient=0&fgnumber=0&fgcli=0&fg=0"
            )
            headers = {"Referer": P2_REPORTS_PAGE, "X-Requested-With": "XMLHttpRequest"}
            if _p2_session is None:
                if not p2_login():
                    return found
            r = _p2_session.get(url, headers=headers, timeout=15)
            body = r.text.strip()
            if r.status_code != 200 or not body or body.startswith("<"):
                print(f"[P2] Bad response ({r.status_code}), re-logging in.")
                _p2_session = None
                if not p2_login():
                    return found
                r = _p2_session.get(url, headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[10]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p2", len(rows))
            if found:
                print(f"[P2] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P2] Fetch error: {e}")
            _record_error("p2")
            _p2_session = None
    return found


# ── Shared OTP processor ──────────────────────────────────────────────────────


def process_new_otps(current):
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
        _dispatch_otp(otp, number, seconds, service)
        print(
            f"[MONITOR] ✅ Forwarded OTP={otp} for {number} ({service}) in {seconds}s"
        )


# ── Global OTP monitors ───────────────────────────────────────────────────────


def panel1_monitor():
    global seen_otps
    print("[P1-MONITOR] Started. Pre-loading existing records...")
    existing = fetch_panel1()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P1-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel1())
        except Exception as e:
            print(f"[P1-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


def panel2_monitor():
    global seen_otps
    print("[P2-MONITOR] Started. Pre-loading existing records...")
    existing = fetch_panel2()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P2-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel2())
        except Exception as e:
            print(f"[P2-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Panel 3 login & fetch (Rabbi1_FD) ────────────────────────────────────────


def p3_login():
    global _p3_session, _p3_csstr
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(P3_LOGIN_PAGE, timeout=15)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if not m:
            print("[P3] Could not find captcha")
            return False
        answer = int(m.group(1)) + int(m.group(2))
        r2 = sess.post(
            P3_SIGNIN_URL,
            data={"username": P3_USER_NAME, "password": P3_PASSWORD, "capt": answer},
            timeout=15,
            allow_redirects=True,
        )
        if "login" in r2.url.lower() or "signin" in r2.url.lower():
            print("[P3] Login failed — still on login page")
            return False
        r3 = sess.get(
            P3_CDR_PAGE, timeout=15, headers={"Referer": P3_BASE_URL + "/agent/"}
        )
        cs = re.search(r"csstr=([a-f0-9]+)", r3.text)
        _p3_csstr = cs.group(1) if cs else ""
        _p3_session = sess
        print(f"[P3] Logged in. csstr={_p3_csstr}")
        return True
    except Exception as e:
        print(f"[P3] Login error: {e}")
        return False


def fetch_panel3():
    global _p3_session, _p3_csstr
    found = {}
    with _p3_lock:
        try:
            today = time.strftime("%Y-%m-%d")

            def build_url():
                return (
                    f"{P3_CDR_DATA_URL}"
                    f"?fdate1={today}%2000:00:00"
                    f"&fdate2={today}%2023:59:59"
                    f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                    f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                    f"&csstr={_p3_csstr or ''}"
                )

            headers = {"Referer": P3_CDR_PAGE, "X-Requested-With": "XMLHttpRequest"}
            if _p3_session is None:
                if not p3_login():
                    return found
            r = _p3_session.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[P3] Bad response ({r.status_code}), re-logging in.")
                _p3_session = None
                if not p3_login():
                    return found
                r = _p3_session.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p3", len(rows))
            if found:
                print(f"[P3] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P3] Fetch error: {e}")
            _record_error("p3")
            _p3_session = None
    return found


def panel3_monitor():
    global seen_otps
    print("[P3-MONITOR] Started. Pre-loading existing records...")
    existing = fetch_panel3()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P3-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel3())
        except Exception as e:
            print(f"[P3-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Panel 4 login & fetch (Rabbi12 / 144.217.71.192) ─────────────────────────


def p4_login():
    global _p4_session, _p4_sesskey
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(P4_LOGIN_PAGE, timeout=15)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if not m:
            print("[P4] Could not find captcha")
            return False
        answer = int(m.group(1)) + int(m.group(2))
        r2 = sess.post(
            P4_SIGNIN_URL,
            data={"username": P4_USER_NAME, "password": P4_PASSWORD, "capt": answer},
            timeout=15,
            allow_redirects=True,
        )
        if "SMSDashboard" not in r2.url and "agent" not in r2.url:
            print(f"[P4] Login failed: {r2.url}")
            return False
        r3 = sess.get(
            P4_CDR_PAGE, timeout=15, headers={"Referer": P4_BASE_URL + "/agent/"}
        )
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        _p4_sesskey = sk.group(1) if sk else ""
        _p4_session = sess
        print(f"[P4] Logged in. sesskey={_p4_sesskey}")
        return True
    except Exception as e:
        print(f"[P4] Login error: {e}")
        return False


def fetch_panel4():
    global _p4_session, _p4_sesskey
    found = {}
    with _p4_lock:
        if not _p4_session and not p4_login():
            return found
        today = time.strftime("%Y-%m-%d")

        def build_url():
            return (
                f"{P4_CDR_DATA_URL}"
                f"?fdate1={today}%2000:00:00&fdate2={today}%2023:59:59"
                f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                f"&sesskey={_p4_sesskey}"
            )

        headers = {"Referer": P4_CDR_PAGE, "X-Requested-With": "XMLHttpRequest"}
        try:
            r = _p4_session.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[P4] Bad response ({r.status_code}), re-logging in.")
                _p4_session = None
                if not p4_login():
                    return found
                r = _p4_session.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p4", len(rows))
            if found:
                print(f"[P4] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P4] Fetch error: {e}")
            _record_error("p4")
            _p4_session = None
    return found


def panel4_monitor():
    global seen_otps
    print("[P4-MONITOR] Started. Pre-loading existing records...")
    existing = fetch_panel4()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P4-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel4())
        except Exception as e:
            print(f"[P4-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Panel 5 login & fetch (Rabbi12_v2 / 51.75.144.178) ───────────────────────


def p5_login():
    global _p5_session, _p5_sesskey
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(P5_LOGIN_PAGE, timeout=15)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if not m:
            print("[P5] Could not find captcha")
            return False
        answer = int(m.group(1)) + int(m.group(2))
        r2 = sess.post(
            P5_SIGNIN_URL,
            data={"username": P5_USER_NAME, "password": P5_PASSWORD, "capt": answer},
            timeout=15,
            allow_redirects=True,
        )
        if "SMSDashboard" not in r2.url and "agent" not in r2.url:
            print(f"[P5] Login failed: {r2.url}")
            return False
        r3 = sess.get(
            P5_CDR_PAGE, timeout=15, headers={"Referer": P5_BASE_URL + "/agent/"}
        )
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        _p5_sesskey = sk.group(1) if sk else ""
        _p5_session = sess
        print(f"[P5] Logged in. sesskey={_p5_sesskey}")
        return True
    except Exception as e:
        print(f"[P5] Login error: {e}")
        return False


def fetch_panel5():
    global _p5_session, _p5_sesskey
    found = {}
    with _p5_lock:
        if not _p5_session and not p5_login():
            return found
        today = time.strftime("%Y-%m-%d")

        def build_url():
            return (
                f"{P5_CDR_DATA_URL}"
                f"?fdate1={today}%2000:00:00&fdate2={today}%2023:59:59"
                f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                f"&sesskey={_p5_sesskey}"
            )

        headers = {"Referer": P5_CDR_PAGE, "X-Requested-With": "XMLHttpRequest"}
        try:
            r = _p5_session.get(build_url(), headers=headers, timeout=15)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[P5] Bad response ({r.status_code}), re-logging in.")
                _p5_session = None
                if not p5_login():
                    return found
                r = _p5_session.get(build_url(), headers=headers, timeout=15)
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip()
                sms_txt = str(row[5]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p5", len(rows))
            if found:
                print(f"[P5] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P5] Fetch error: {e}")
            _record_error("p5")
            _p5_session = None
    return found


def panel5_monitor():
    global seen_otps
    print("[P5-MONITOR] Started. Pre-loading existing records...")
    existing = fetch_panel5()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P5-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel5())
        except Exception as e:
            print(f"[P5-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Panel 6 login & fetch (TrueSMS.net / SMSRanges) ──────────────────────────


def p6_login():
    global _p6_session, _p6_sesskey
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        r = sess.get(P6_LOGIN_PAGE, timeout=20, verify=False)
        m = re.search(r"What is (\d+) \+ (\d+)", r.text)
        if m:
            answer = int(m.group(1)) + int(m.group(2))
            r2 = sess.post(
                P6_SIGNIN_URL,
                data={
                    "username": P6_USER_NAME,
                    "password": P6_PASSWORD,
                    "capt": answer,
                },
                timeout=20,
                allow_redirects=True,
                verify=False,
            )
        else:
            r2 = sess.post(
                P6_SIGNIN_URL,
                data={"username": P6_USER_NAME, "password": P6_PASSWORD},
                timeout=20,
                allow_redirects=True,
                verify=False,
            )
        if "login" in r2.url.lower() and "agent" not in r2.url.lower():
            print(f"[P6] Login failed: {r2.url}")
            return False
        r3 = sess.get(
            P6_CDR_PAGE,
            timeout=20,
            headers={"Referer": P6_BASE_URL + "/agent/"},
            verify=False,
        )
        sk = re.search(r"sesskey=([A-Za-z0-9+/=]+)", r3.text)
        cs = re.search(r"csstr=([a-f0-9]+)", r3.text)
        _p6_sesskey = sk.group(1) if sk else (cs.group(1) if cs else "")
        _p6_session = sess
        print(f"[P6] Logged in. token={_p6_sesskey[:10] if _p6_sesskey else 'none'}")
        return True
    except Exception as e:
        print(f"[P6] Login error: {e}")
        return False


def fetch_panel6():
    global _p6_session, _p6_sesskey
    found = {}
    with _p6_lock:
        try:
            today = time.strftime("%Y-%m-%d")

            def build_url():
                return (
                    f"{P6_CDR_DATA_URL}"
                    f"?fdate1={today}%2000:00:00"
                    f"&fdate2={today}%2023:59:59"
                    f"&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth="
                    f"&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
                    f"&sesskey={_p6_sesskey or ''}"
                )

            headers = {"Referer": P6_CDR_PAGE, "X-Requested-With": "XMLHttpRequest"}
            if _p6_session is None:
                if not p6_login():
                    return found
            r = _p6_session.get(build_url(), headers=headers, timeout=20, verify=False)
            body = r.text.strip()
            if (
                r.status_code != 200
                or not body
                or body.startswith("<")
                or "Direct Script" in body
            ):
                print(f"[P6] Bad response ({r.status_code}), re-logging in.")
                _p6_session = None
                if not p6_login():
                    return found
                r = _p6_session.get(
                    build_url(), headers=headers, timeout=20, verify=False
                )
                body = r.text.strip()
            rows = json.loads(body).get("aaData", [])
            for row in rows:
                if not isinstance(row[0], str):
                    continue
                number = str(row[2]).strip()
                service = str(row[3]).strip() if len(row) > 3 else "TrueSMS"
                sms_txt = str(row[5]).strip() if len(row) > 5 else ""
                if not sms_txt and len(row) > 4:
                    sms_txt = str(row[4]).strip()
                otp = extract_otp_from_sms(sms_txt)
                if otp:
                    key = f"{number}:{sms_txt}"
                    found[key] = (number, otp, sms_txt, service)
            _record_fetch("p6", len(rows))
            if found:
                print(f"[P6] ✅ Fetched {len(found)} records.")
        except Exception as e:
            print(f"[P6] Fetch error: {e}")
            _record_error("p6")
            _p6_session = None
    return found


def panel6_monitor():
    global seen_otps
    print("[P6-MONITOR] Started (TrueSMS/SMSRanges). Pre-loading existing records...")
    existing = fetch_panel6()
    with seen_lock:
        for key in existing:
            seen_otps[key] = True
        save_json(SEEN_FILE, seen_otps)
    print(f"[P6-MONITOR] Pre-loaded {len(existing)} records. Watching for new ones...")
    while True:
        try:
            process_new_otps(fetch_panel6())
        except Exception as e:
            print(f"[P6-MONITOR] Loop error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Demo OTP monitor ──────────────────────────────────────────────────────────


def demo_monitor():
    print("[DEMO] Thread started.")
    while True:
        now = time.time()
        with _demo_lock:
            configs = list(_demo_configs)
        for cfg in configs:
            if not cfg.get("active"):
                continue
            cid = cfg["id"]
            if now >= _demo_next_fire.get(cid, 0):
                _demo_next_fire[cid] = now + cfg["interval"]
                services = cfg.get("services") or ["Facebook"]
                for svc in services:
                    otp = "".join([str(random.randint(0, 9)) for _ in range(cfg["digits"])])
                    number = random.choice(cfg["numbers"])
                    try:
                        send_otp_message(get_otp_group_id(), otp, number, "—", svc)
                    except Exception as e:
                        print(f"[DEMO] {cfg['name']} send error ({svc}): {e}")
        time.sleep(1)


def demo_status_text():
    with _demo_lock:
        configs = list(_demo_configs)
    running = [c for c in configs if c.get("active")]
    status = f"🟢 <b>{len(running)} টি চলছে</b>" if running else "🔴 <b>সব বন্ধ</b>"
    lines = (
        f"🎭🔥 <b>DEMO OTP PANEL</b> 🔥🎭\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"📡 <b>Status ▸▸</b>  {status}\n"
        f"📋 <b>Configs:</b>  {len(configs)} টি\n\n"
    )
    for cfg in configs:
        icon = "🟢" if cfg.get("active") else "🔴"
        svcs = ", ".join(cfg.get("services") or ["?"])
        nums = cfg["numbers"]
        lines += (
            f"{icon} <b>{cfg['name']}</b>\n"
            f"  💬 {svcs}  |  🔢 {cfg['digits']} digits  |  ⏱️ {cfg['interval']}s  |  📱 {len(nums)} num\n\n"
        )
    lines += "⚡━━━━━━━━━━━━━━━━⚡"
    return lines


def demo_cfg_inline_markup():
    with _demo_lock:
        configs = list(_demo_configs)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cfg in configs:
        icon = "⏹️ Stop" if cfg.get("active") else "▶️ Start"
        action = "stop" if cfg.get("active") else "start"
        markup.add(
            types.InlineKeyboardButton(
                f"{icon}  {cfg['name']}",
                callback_data=f"cfg_toggle:{cfg['id']}:{action}",
            )
        )
    return markup


def demo_menu_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    with _demo_lock:
        cfg_count = len(_demo_configs)
    m.add("➕ 𝗖𝗼𝗻𝗳𝗶𝗴 𝗬𝗼𝗴 𝗞𝗼𝗿𝗼")
    if cfg_count > 0:
        m.add("🗑️ 𝗖𝗼𝗻𝗳𝗶𝗴 𝗠𝘂𝗰𝗵𝗼")
    m.add("🔙 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟")
    return m


# ── Menus ─────────────────────────────────────────────────────────────────────


def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("☎️ 𝗡𝗨𝗠𝗕𝗔𝗥 ☎️"))
    markup.add(types.KeyboardButton("📊 𝗦𝗧𝗢𝗖𝗞"), types.KeyboardButton("📞 𝗦𝗔𝗣𝗢𝗥𝗧"))
    if user_id in ADMIN_IDS:
        markup.add(types.KeyboardButton("⚙️ 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 ⚙️"))
    return markup


def save_services():
    save_json(SERVICES_FILE, _services)


def _get_svc_map():
    return {s["label"]: s["key"] for s in _services}


SERVICE_BUTTON_MAP = {}


def show_services(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btns = [types.KeyboardButton(s["label"]) for s in _services]
    for i in range(0, len(btns), 2):
        markup.add(*btns[i:i + 2])
    markup.add(types.KeyboardButton("🔙 Main Menu"))
    bot.send_message(
        message.chat.id,
        "🛠 <b>Select Service:</b>",
        reply_markup=markup,
        parse_mode="HTML",
    )


def show_countries(chat_id, svc):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    if svc in stock:
        for cnt, nums in stock[svc].items():
            if nums:
                _, flag = get_country_details(nums[0])
                btns.append(
                    types.InlineKeyboardButton(
                        f"{flag} {cnt}", callback_data=f"n:{svc}:{cnt}"
                    )
                )
    if btns:
        markup.add(*btns)
    markup.add(
        types.InlineKeyboardButton("⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_to_services")
    )
    bot.send_message(
        chat_id,
        f"🔥 <b>{svc.upper()} — COUNTRY SELECT</b> 🔥",
        reply_markup=markup,
        parse_mode="HTML",
    )


# ── Handlers ──────────────────────────────────────────────────────────────────


@bot.message_handler(commands=["start"])
def start_cmd(message):
    u = message.from_user
    register_user(
        message.chat.id,
        first_name=u.first_name or "",
        last_name=u.last_name or "",
        username=u.username or "",
    )
    uname = f"@{u.username}" if u.username else (u.first_name or "User")
    uid_str = u.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔥 𝗢𝗧𝗣 𝗚𝗿𝘂𝗽 𝗝𝗢𝗜𝗡 🔥", url=get_otp_group_link() or CHANNEL_1))
    markup.add(types.InlineKeyboardButton("📢 𝗠𝗮𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗝𝗢𝗜𝗡", url=get_channel2()))
    markup.add(types.InlineKeyboardButton("✅ 𝗩𝗘𝗥𝗜𝗙𝗬 𝗞𝗢𝗥𝗢 ✅", callback_data="v"))
    bot.send_message(
        message.chat.id,
        get_template("start").format(uname=uname, uid=uid_str),
        reply_markup=markup,
        parse_mode="HTML",
    )


@bot.message_handler(commands=["test"])
def test_cmd(message):
    fake_otp = str(random.randint(100000, 999999))
    fake_number = "8801712345678"
    fake_svc = "Instagram"
    fake_secs = 12
    send_otp_message(message.chat.id, fake_otp, fake_number, fake_secs, fake_svc)
    try:
        send_otp_message(get_otp_group_id(), fake_otp, fake_number, fake_secs, fake_svc)
        bot.send_message(
            message.chat.id, "✅ Group-eও pathano hoyeche!", parse_mode="HTML"
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠️ Group-e pathate parina: <code>{e}</code>",
            parse_mode="HTML",
        )


@bot.message_handler(commands=["panels"])
def panels_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    with _stats_lock:
        stats = {k: dict(v) for k, v in _panel_stats.items()}
    lines = ""
    for pid in ["p1", "p2", "p3", "p4", "p5", "p6"]:
        s = stats.get(pid, {})
        if s.get("last"):
            ago = int(time.time() - s["last"])
            last_str = f"{ago}s ago"
        else:
            last_str = "never"
        err_str = f"  ⚠️ {s['errors']} err" if s.get("errors") else ""
        lines += (
            f"{s.get('status', '⏳')} <b>{s.get('name', '?')}</b>\n"
            f"   🌐 <code>{s.get('host', '?')}</code>\n"
            f"   📊 {s.get('count', 0)} records  •  🕐 {last_str}{err_str}\n\n"
        )
    with _demo_lock:
        demo_on = _demo_active
    demo_str = "🟢 Running" if demo_on else "🔴 Stopped"
    bot.send_message(
        message.chat.id,
        f"📡 <b>PANEL STATUS</b>\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"{lines}"
        f"🎭 <b>Demo OTP:</b>  {demo_str}\n\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n"
        f"🔄 <i>Updates every {POLL_INTERVAL}s</i>",
        parse_mode="HTML",
    )
    dp_copy = list(_dynamic_panels)
    if dp_copy:
        dp_lines = ""
        for p in dp_copy:
            pid = p["id"]
            with _stats_lock:
                s = _panel_stats.get(pid, {})
            st = s.get("status", "⏳")
            cnt = s.get("count", 0)
            err = s.get("errors", 0)
            t = s.get("last")
            last_str = f"{int(time.time() - t)}s ago" if t else "never"
            err_str = f"  ⚠️ {err} err" if err else ""
            dp_lines += (
                f"{st} <b>{p.get('username', '?')}</b> <code>[{pid}]</code>\n"
                f"   🌐 <code>{p.get('host', '?')}</code>\n"
                f"   📊 {cnt} records  •  🕐 {last_str}{err_str}\n\n"
            )
        bot.send_message(
            message.chat.id,
            f"📡 <b>DYNAMIC PANELS</b>\n"
            f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
            f"{dp_lines}"
            f"💡 <i>/addpanel diye naya panel add koro</i>",
            parse_mode="HTML",
        )


@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(
        message.chat.id,
        "✍️ <b>Broadcast content পাঠাও:</b> \n\n"
        "📝 Text\n🖼️ Photo\n🎥 Video\n🎭 Sticker\n"
        "🎞️ GIF / Animation\n🎵 Audio / Music\n🎤 Voice message\n📎 Document / APK / ZIP / PDF\n\n"
        "<i>Caption support ache — sob kichute!</i>",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, do_broadcast)


def _clr_service_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    services = [
        ("facebook", "💬"),
        ("instagram", "📸"),
        ("whatsapp", "📱"),
        ("telegram", "✈️"),
        ("binance", "🪙"),
        ("pc clone", "💻"),
    ]
    for svc, icon in services:
        total = sum(len(v) for v in stock.get(svc, {}).values())
        markup.add(
            types.InlineKeyboardButton(
                f"{icon} {svc.upper()} ({total})", callback_data=f"clr_s:{svc}"
            )
        )
    markup.add(types.InlineKeyboardButton(" Clear ALL Stock", callback_data="clr_all"))
    return markup


@bot.message_handler(commands=["addpanel"])
def addpanel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    _addpanel_state[message.from_user.id] = {"step": "url", "data": {}}
    msg = bot.send_message(
        message.chat.id,
        "🔧🔥 <b>ADD NEW PANEL</b> 🔥🔧\n\n"
        "📡 <b>Step 1/3:</b> Panel URL pathao\n"
        "<i>Example: http://1.2.3.4/ints/agent/SMSCDRStats</i>",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _ap_get_url)


def _ap_get_url(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _addpanel_state.pop(message.from_user.id, None)
        _go_admin_panel(message)
        return
    url = (message.text or "").strip()
    base_url = None
    panel_type = "smscdr"
    m_ints = re.match(r"(https?://[^/]+/(?:ints|sms))(?:/|$)", url)
    m_agent = re.match(r"(https?://[^/]+)/agent/(SMSCDRStats|SMSRanges)", url, re.IGNORECASE)
    m_domain = re.match(r"(https?://[^/?#]+)/?$", url)
    if m_ints:
        base_url = m_ints.group(1)
        panel_type = "smscdr"
    elif m_agent:
        base_url = m_agent.group(1)
        panel_type = "smsranges" if m_agent.group(2).lower() == "smsranges" else "smscdr"
    elif m_domain:
        base_url = m_domain.group(1)
        panel_type = "smscdr"
    if not base_url:
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid URL dao:\n"
            "• <code>http://1.2.3.4/ints/agent/SMSCDRStats</code>\n"
            "• <code>https://truesms.net/agent/SMSCDRStats</code>\n"
            "• <code>https://truesms.net/agent/SMSRanges</code>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _ap_get_url)
        return
    host_m = re.search(r"//([^/]+)", base_url)
    uid = message.from_user.id
    _addpanel_state[uid]["data"]["base_url"] = base_url
    _addpanel_state[uid]["data"]["host"] = host_m.group(1) if host_m else base_url
    _addpanel_state[uid]["data"]["panel_type"] = panel_type
    type_label = "SMSRanges" if panel_type == "smsranges" else "SMSCDRStats"
    msg = bot.send_message(
        message.chat.id,
        f"✅ URL: <code>{base_url}</code>\n"
        f"📊 Type: <b>{type_label}</b>\n\n"
        f"👤 <b>Step 2/3:</b> Username pathao:",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _ap_get_user)


def _ap_get_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _addpanel_state.pop(message.from_user.id, None)
        _go_admin_panel(message)
        return
    username = (message.text or "").strip()
    if not username:
        msg = bot.send_message(message.chat.id, "❌ Username dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _ap_get_user)
        return
    _addpanel_state[message.from_user.id]["data"]["username"] = username
    msg = bot.send_message(
        message.chat.id,
        f"✅ Username: <code>{username}</code>\n\n🔑 <b>Step 3/3:</b> Password pathao:",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _ap_get_pass)


def _ap_get_pass(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    uid = message.from_user.id
    if _is_back(message.text):
        _addpanel_state.pop(uid, None)
        _go_admin_panel(message)
        return
    password = (message.text or "").strip()
    if not password:
        msg = bot.send_message(message.chat.id, "❌ Password dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _ap_get_pass)
        return
    data = _addpanel_state.get(uid, {}).get("data", {})
    data["password"] = password
    wait_msg = bot.send_message(
        message.chat.id,
        "⏳🔥 <b>Connection test korchi...</b>\n<i>Ektu wait koro!</i>",
        parse_mode="HTML",
    )
    panel_id = f"d{int(time.time()) % 100000}"
    panel = {
        "id": panel_id,
        "host": data.get("host", ""),
        "base_url": data.get("base_url", ""),
        "username": data.get("username", ""),
        "password": password,
        "panel_type": data.get("panel_type", "smscdr"),
    }
    sess, token = _ints_login(panel)
    try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception:
        pass
    if not sess:
        bot.send_message(
            message.chat.id,
            "❌ <b>Connection FAILED!</b> ❌\n\n"
            "⚠️ URL, username ba password check koro.\n"
            "Aro try korte /addpanel pathao.",
            parse_mode="HTML",
        )
        _addpanel_state.pop(uid, None)
        return
    _dynamic_sessions[panel_id] = {"session": sess, "token": token}
    _dynamic_panels.append(panel)
    save_dynamic_panels()
    _start_dynamic_panel(panel)
    bot.send_message(
        message.chat.id,
        f"✅🔥 <b>PANEL ADDED & STARTED!</b> 🔥✅\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"🆔 <b>ID     ▸▸</b> <code>{panel_id}</code>\n"
        f"🌐 <b>Host   ▸▸</b> <code>{data['host']}</code>\n"
        f"👤 <b>User   ▸▸</b> <code>{data['username']}</code>\n\n"
        f"📡 Monitor thread started! /panels diye check koro.",
        parse_mode="HTML",
    )
    _addpanel_state.pop(uid, None)


def _svc_get_label(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _addservice_state.pop(message.from_user.id, None)
        _go_admin_panel(message)
        return
    label = (message.text or "").strip()
    if not label:
        msg = bot.send_message(message.chat.id, "❌ Label dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _svc_get_label)
        return
    _addservice_state[message.from_user.id]["label"] = label
    msg = bot.send_message(
        message.chat.id,
        f"✅ Label: <b>{label}</b>\n\n"
        "🔑 <b>Step 2/2:</b> Internal key dao (lowercase, no space)\n"
        "<i>Example: telegram, binance, tiktok</i>",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _svc_get_key)


def _svc_get_key(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _addservice_state.pop(message.from_user.id, None)
        _go_admin_panel(message)
        return
    key = (message.text or "").strip().lower()
    if not key:
        msg = bot.send_message(message.chat.id, "❌ Key dao:", reply_markup=_back_admin_kb())
        bot.register_next_step_handler(msg, _svc_get_key)
        return
    label = _addservice_state.get(message.from_user.id, {}).get("label", "")
    existing_keys = [s["key"] for s in _services]
    if key in existing_keys:
        msg = bot.send_message(
            message.chat.id,
            f"❌ Key <code>{key}</code> already ache! Onnyo key dao:",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _svc_get_key)
        return
    _services.append({"label": label, "key": key})
    save_services()
    _addservice_state.pop(message.from_user.id, None)
    _go_admin_panel(
        message,
        f"✅🔥 <b>Service Added!</b>\n\n"
        f"🏷️ Label: <b>{label}</b>\n"
        f"🔑 Key: <code>{key}</code>\n\n"
        f"<i>Service menu-te dekha jabe!</i>",
    )


@bot.message_handler(commands=["listpanels"])
def listpanels_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not _dynamic_panels:
        bot.send_message(
            message.chat.id,
            "📋 No dynamic panels yet.\n💡 /addpanel diye add koro.",
            parse_mode="HTML",
        )
        return
    lines = "📋🔥 <b>DYNAMIC PANELS LIST</b> 🔥📋\n⚡━━━━━━━━━━━━━━━━⚡\n\n"
    for p in _dynamic_panels:
        pid = p["id"]
        with _stats_lock:
            s = _panel_stats.get(pid, {})
        st = s.get("status", "⏳")
        lines += (
            f"{st} 🆔 <code>{pid}</code>\n"
            f"   🌐 <code>{p.get('host', '?')}</code>\n"
            f"   👤 {p.get('username', '?')}\n\n"
        )
    lines += "🗑️ Remove: <code>/removepanel [ID]</code>"
    bot.send_message(message.chat.id, lines, parse_mode="HTML")


@bot.message_handler(commands=["removepanel"])
def removepanel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(
            message.chat.id,
            "❌ Panel ID dao:\n<code>/removepanel d12345</code>\n\n"
            "💡 /listpanels diye ID dekho.",
            parse_mode="HTML",
        )
        return
    pid = args[1].strip()
    before = len(_dynamic_panels)
    _dynamic_panels[:] = [p for p in _dynamic_panels if p["id"] != pid]
    if len(_dynamic_panels) < before:
        save_dynamic_panels()
        with _stats_lock:
            _panel_stats.pop(pid, None)
        _dynamic_sessions.pop(pid, None)
        _dynamic_locks.pop(pid, None)
        bot.send_message(
            message.chat.id,
            f"✅🔥 Panel <code>{pid}</code> removed!\n"
            f"<i>Monitor thread will stop naturally.</i>",
            parse_mode="HTML",
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Panel <code>{pid}</code> not found.\n"
            f"💡 /listpanels diye ID check koro.",
            parse_mode="HTML",
        )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global stock
    try:
        data = call.data

        if data == "v":
            uid = call.from_user.id

            grp_id = get_otp_group_id()
            grp_link = get_otp_group_link()
            ch2_link = get_channel2()
            ch2_ref = _extract_username(ch2_link)

            not_joined = []

            grp_ok = _check_member(grp_id, uid) if grp_id else None
            if grp_ok is False:
                not_joined.append(("🔥 OTP Group", grp_link))

            ch2_ok = _check_member(ch2_ref, uid) if ch2_ref else None
            if ch2_ok is False:
                not_joined.append(("📢 Main Channel", ch2_link))

            if not_joined:
                bot.answer_callback_query(call.id, "❌ Sob jagay join hao nai!", show_alert=False)
                lines = "❌ <b>Verify hote parcho na!</b>\n\n"
                lines += "⛔ Tumi ekhono nicher jagay join hao nai:\n\n"
                for name, _ in not_joined:
                    lines += f"  🚫 <b>{name}</b>\n"
                lines += "\n👇 Join kore <b>Verify Koro</b> te click koro:"
                err_markup = types.InlineKeyboardMarkup(row_width=1)
                for name, lnk in not_joined:
                    err_markup.add(types.InlineKeyboardButton(
                        f"👉 {name}-e JOIN KORO", url=lnk
                    ))
                err_markup.add(types.InlineKeyboardButton(
                    "🔄 Verify Koro", callback_data="v"
                ))
                try:
                    bot.edit_message_text(
                        lines,
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=err_markup,
                        parse_mode="HTML",
                    )
                except Exception:
                    bot.send_message(
                        call.message.chat.id,
                        lines,
                        reply_markup=err_markup,
                        parse_mode="HTML",
                    )
            else:
                bot.delete_message(call.message.chat.id, call.message.message_id)
                vname = call.from_user.first_name or call.from_user.username or "User"
                bot.send_message(
                    call.message.chat.id,
                    get_template("verify_success").format(vname=vname, uid=uid),
                    reply_markup=main_menu(call.from_user.id),
                    parse_mode="HTML",
                )

        elif data == "back_to_services":
            show_services(call.message)

        elif data.startswith("s:"):
            svc = data.split(":")[1]
            markup = types.InlineKeyboardMarkup(row_width=2)
            btns = []
            if svc in stock:
                for cnt, nums in stock[svc].items():
                    if nums:
                        _, flag = get_country_details(nums[0])
                        btns.append(
                            types.InlineKeyboardButton(
                                f" {flag} {cnt}", callback_data=f"n:{svc}:{cnt}"
                            )
                        )
            if btns:
                markup.add(*btns)
            markup.add(
                types.InlineKeyboardButton("⬅️ 𝗕𝗮𝗰𝗸", callback_data="back_to_services")
            )
            bot.edit_message_text(
                f"🔥 <b>{svc.upper()} — COUNTRY</b> 🔥",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data.startswith("n:"):
            _, svc, scnt = data.split(":")
            if scnt in stock.get(svc, {}) and stock[svc][scnt]:
                num = stock[svc][scnt].pop(0)
                save_stock()
                c_name, flag = get_country_details(num)
                register_number(call.message.chat.id, num)
                display_num = num if num.startswith("+") else "+" + num
                init_kb = types.InlineKeyboardMarkup(row_width=2)
                init_kb.add(
                    types.InlineKeyboardButton("🔄 New Number", callback_data=f"n:{svc}:{scnt}"),
                    types.InlineKeyboardButton("🌍 Change Country", callback_data=f"s:{svc}"),
                )
                init_kb.add(
                    types.InlineKeyboardButton("📢 OTP Group", url=get_otp_group_link()),
                )
                res = get_template("number_assigned").format(
                    svc=svc.capitalize(), flag=flag, country=c_name, number=display_num
                )
                bot.edit_message_text(
                    res,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=init_kb,
                    parse_mode="HTML",
                )
                _start_countdown(
                    call.message.chat.id,
                    call.message.message_id,
                    svc, flag, c_name, display_num, scnt,
                )
                bot.send_message(
                    call.message.chat.id,
                    "🏚️<b>MAIN MENU</b>",
                    reply_markup=main_menu(call.from_user.id),
                    parse_mode="HTML",
                )
            else:
                bot.answer_callback_query(call.id, " STOCK SHESH! ", show_alert=True)

        elif data == "clr_menu":
            if call.from_user.id not in ADMIN_IDS:
                return
            bot.edit_message_text(
                "🗑️🔥 <b>STOCK CLEAR PANEL</b> 🔥🗑️\n\n"
                " <b>Kon service-er stock clear korbe?</b>\n"
                "⬇️ Service choose koro:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_clr_service_markup(),
                parse_mode="HTML",
            )

        elif data.startswith("clr_s:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            svc = data[6:]
            markup = types.InlineKeyboardMarkup(row_width=1)
            svc_stock = stock.get(svc, {})
            has_any = False
            for cnt, nums in svc_stock.items():
                if nums:
                    has_any = True
                    _, flag = get_country_details(nums[0])
                    cb = f"clr_c:{svc}:{cnt}"
                    if len(cb.encode()) <= 64:
                        markup.add(
                            types.InlineKeyboardButton(
                                f"🗑️ {flag} {cnt}  ({len(nums)} টি)", callback_data=cb
                            )
                        )
            if not has_any:
                markup.add(
                    types.InlineKeyboardButton("⚠️ Stock nai!", callback_data="clr_menu")
                )
            markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="clr_menu"))
            bot.edit_message_text(
                f"🔥 <b>{svc.upper()} — Kon desh clear korbe?</b> 🔥\n\n"
                f"⬇️ Country choose koro:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data.startswith("clr_c:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            _, svc, cnt = data.split(":", 2)
            count = len(stock.get(svc, {}).get(cnt, []))
            _, flag = get_country_details(stock[svc][cnt][0]) if count else ("", "🌐")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton(
                    "✅ Haa, Delete Koro", callback_data=f"clr_y:{svc}:{cnt}"
                ),
                types.InlineKeyboardButton("❌ Cancel", callback_data=f"clr_s:{svc}"),
            )
            bot.edit_message_text(
                f"⚠️ <b>CONFIRM DELETE</b> ⚠️\n\n"
                f"💬 <b>Service ▸▸</b>  {svc.upper()}\n"
                f"🌍 <b>Country ▸▸</b>  {flag} {cnt}\n"
                f"📱 <b>Numbers ▸▸</b>  {count} টি\n\n"
                f" Sure? Ei {count} টি number delete hoye jabe!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data.startswith("clr_y:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            _, svc, cnt = data.split(":", 2)
            removed = len(stock.get(svc, {}).get(cnt, []))
            if svc in stock and cnt in stock[svc]:
                del stock[svc][cnt]
                save_stock()
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🗑️ Aro Clear", callback_data=f"clr_s:{svc}"),
                types.InlineKeyboardButton("🔙 Services", callback_data="clr_menu"),
            )
            bot.edit_message_text(
                f"✅🔥 <b>DELETE COMPLETE!</b> 🔥✅\n\n"
                f"💬 <b>Service ▸▸</b>  {svc.upper()}\n"
                f"🌍 <b>Country ▸▸</b>  {cnt}\n"
                f"📱 <b>Deleted  ▸▸</b>  {removed} টি number\n\n"
                f"⚡ <i>Stock update hoyeche!</i>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data == "clr_all":
            if call.from_user.id not in ADMIN_IDS:
                return
            total = sum(
                len(nums) for svc_d in stock.values() for nums in svc_d.values()
            )
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton(
                    " Haa, SOB Clear", callback_data="clr_allok"
                ),
                types.InlineKeyboardButton("❌ Cancel", callback_data="clr_menu"),
            )
            bot.edit_message_text(
                f"☠️⚠️ <b>CLEAR ALL CONFIRM</b> ⚠️☠️\n\n"
                f" Total <b>{total} টি</b> number delete hobe!\n"
                f"⚡ Sob service-er sob country mochhe jabe!\n\n"
                f"🔥 Sure? Eta undo kora jabe na!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data == "clr_allok":
            if call.from_user.id not in ADMIN_IDS:
                return
            stock = {
                "whatsapp": {},
                "facebook": {},
                "telegram": {},
                "instagram": {},
                "pc clone": {},
                "binance": {},
            }
            save_stock()
            bot.edit_message_text(
                "🔥 <b>SOB STOCK CLEAR HOYECHE!</b> 🔥\n <i>Ekhon naya number add koro!</i> ",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
            )

        elif data.startswith("rmpanel:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            pid = data.split(":", 1)[1]
            before = len(_dynamic_panels)
            _dynamic_panels[:] = [p for p in _dynamic_panels if p["id"] != pid]
            if len(_dynamic_panels) < before:
                save_dynamic_panels()
                with _stats_lock:
                    _panel_stats.pop(pid, None)
                _dynamic_sessions.pop(pid, None)
                _dynamic_locks.pop(pid, None)
                bot.edit_message_text(
                    f"✅🔥 <b>Panel <code>{pid}</code> removed!</b>\n"
                    f"<i>Monitor thread will stop naturally.</i>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                )
            else:
                bot.answer_callback_query(call.id, "❌ Panel pawa jaini!", show_alert=True)

        elif data.startswith("rmsvc:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            key = data.split(":", 1)[1]
            before = len(_services)
            _services[:] = [s for s in _services if s["key"] != key]
            if len(_services) < before:
                save_services()
                bot.edit_message_text(
                    f"✅🔥 <b>Service <code>{key}</code> removed!</b>\n"
                    f"<i>Service menu theke hatiye dewa hoyeche.</i>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                )
            else:
                bot.answer_callback_query(call.id, "❌ Service pawa jaini!", show_alert=True)

        elif data.startswith("rmadmin:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            target = int(data.split(":")[1])
            if remove_admin(target):
                name = user_names.get(str(target), {}).get("first_name", "") or str(target)
                bot.answer_callback_query(call.id, f"✅ {name} removed!", show_alert=False)
                try:
                    bot.edit_message_text(
                        f"✅ <b>ADMIN REMOVED!</b>\n\n"
                        f"🗑️ <b>Removed:</b> {name} [<code>{target}</code>]\n\n"
                        f"<i>Ekhon theke ei user admin access harabe.</i>",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Remove kora gelo na (Super Admin)!", show_alert=True)

        elif data.startswith("cfg_toggle:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            parts = data.split(":")
            try:
                cid = int(parts[1])
                action = parts[2]
            except (IndexError, ValueError):
                bot.answer_callback_query(call.id, "❌ Error!", show_alert=True)
                return
            with _demo_lock:
                for cfg in _demo_configs:
                    if cfg["id"] == cid:
                        cfg["active"] = (action == "start")
                        cfg_name = cfg["name"]
                        break
                else:
                    bot.answer_callback_query(call.id, "❌ Config পাওয়া যায়নি!", show_alert=True)
                    return
            if action == "start":
                _demo_next_fire[cid] = 0
                status_msg = f"🟢 <b>{cfg_name} চালু হয়েছে!</b>"
            else:
                _demo_next_fire.pop(cid, None)
                status_msg = f"🔴 <b>{cfg_name} বন্ধ হয়েছে!</b>"
            bot.answer_callback_query(call.id, status_msg.replace("<b>", "").replace("</b>", ""), show_alert=False)
            try:
                bot.edit_message_text(
                    "⚡ <b>Config Start/Stop:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=demo_cfg_inline_markup(),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            bot.send_message(
                call.message.chat.id,
                status_msg + "\n\n" + demo_status_text(),
                parse_mode="HTML",
            )

        elif data.startswith("rmcfg:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            try:
                cid = int(data.split(":", 1)[1])
            except ValueError:
                bot.answer_callback_query(call.id, "❌ Invalid config!", show_alert=True)
                return
            with _demo_lock:
                before = len(_demo_configs)
                _demo_configs[:] = [c for c in _demo_configs if c["id"] != cid]
                removed = before > len(_demo_configs)
            if removed:
                _demo_next_fire.pop(cid, None)
                try:
                    bot.edit_message_text(
                        f"✅🔥 <b>Config মুছে গেছে!</b>\n\n" + demo_status_text(),
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Config পাওয়া যায়নি!", show_alert=True)

        elif data.startswith("editmsg:"):
            if call.from_user.id not in ADMIN_IDS:
                return
            key = data.split(":", 1)[1]
            if key in _TEMPLATE_LABELS:
                _ask_new_template(call, key)
            else:
                bot.answer_callback_query(call.id, "❌ Unknown template!", show_alert=True)

        elif data == "editmsg_reset_all":
            if call.from_user.id not in ADMIN_IDS:
                return
            _templates.update(_DEFAULT_TEMPLATES)
            save_templates()
            try:
                bot.edit_message_text(
                    "✅🔥 <b>সব মেসেজ Default এ Reset হয়েছে!</b>\n\n"
                    "<i>এখন থেকে সব মেসেজ Default ফরমেটে যাবে।</i>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                )
            except Exception:
                pass

        elif data == "grp_info":
            if call.from_user.id not in ADMIN_IDS:
                return
            _show_settings_inline(call)

        elif data == "set_autodel":
            if call.from_user.id not in ADMIN_IDS:
                return
            cur = _group_settings.get("auto_delete", True)
            _group_settings["auto_delete"] = not cur
            save_group_settings()
            bot.answer_callback_query(
                call.id,
                "✅ Auto Delete: " + ("🟢 ON" if not cur else "🔴 OFF"),
                show_alert=False,
            )
            _show_settings_inline(call)

        elif data == "set_channel2":
            if call.from_user.id not in ADMIN_IDS:
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id,
                "📢 <b>Notun Join Channel link dao:</b>\n\n"
                "<i>Example: https://t.me/aR_OTP_rcv</i>",
                reply_markup=_back_admin_kb(),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, _sett_get_channel2)

        elif data == "set_botlink":
            if call.from_user.id not in ADMIN_IDS:
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id,
                "🤖 <b>Notun Bot link dao:</b>\n\n"
                "<i>Example: https://t.me/ar_otp_bot</i>",
                reply_markup=_back_admin_kb(),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, _sett_get_botlink)

        elif data == "grp_setlink":
            if call.from_user.id not in ADMIN_IDS:
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id,
                "🔗 <b>Notun OTP Group Link dao:</b>\n\n"
                "<i>Example: https://t.me/aR_OTP_rcv</i>",
                reply_markup=_back_admin_kb(),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, _grp_get_link)

        elif data == "grp_setid":
            if call.from_user.id not in ADMIN_IDS:
                return
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id,
                "🆔 <b>Notun OTP Group Chat ID dao:</b>\n\n"
                "<i>Example: -1001234567890</i>\n"
                "⚠️ Negative number dite hobe (group ID always negative)",
                reply_markup=_back_admin_kb(),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, _grp_get_id)

        elif data == "grp_remove":
            if call.from_user.id not in ADMIN_IDS:
                return
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Haa, Remove", callback_data="grp_removeok"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="grp_info"),
            )
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                "⚠️ <b>CONFIRM GROUP REMOVE</b> ⚠️\n\n"
                "OTP Group setting reset hobe!\n"
                "Group-e aro OTP pathano bondho hobe.\n\n"
                "Sure?",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML",
            )

        elif data == "grp_removeok":
            if call.from_user.id not in ADMIN_IDS:
                return
            _group_settings["otp_group_id"] = None
            _group_settings["otp_group_link"] = ""
            save_group_settings()
            bot.answer_callback_query(call.id, "✅ Group removed!")
            _show_settings_inline(call)

    except Exception as e:
        print(f"Callback Error: {e}")


# ── Excel / CSV helpers ───────────────────────────────────────────────────────

VALID_SERVICES = [
    "facebook",
    "instagram",
    "whatsapp",
    "telegram",
    "binance",
    "pc clone",
]


def _parse_spreadsheet(data: bytes, filename: str):
    """
    Parse Excel (.xlsx / .xls) or CSV file.
    Returns:
      - (rows, mode)
        mode='two_col' → rows = list of (service, number)
        mode='one_col' → rows = list of number strings
    Accepts header rows with 'service'/'number' labels.
    Falls back: 2-column files = service+number, 1-column = numbers only.
    """
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
            cleaned = [
                str(ws.cell_value(ri, ci)).strip()
                for ci in range(ws.ncols)
                if str(ws.cell_value(ri, ci)).strip()
            ]
            if cleaned:
                raw_rows.append(cleaned)
    else:
        return [], "unknown"

    if not raw_rows:
        return [], "empty"

    # Detect header row
    start = 0
    first = [c.lower() for c in raw_rows[0]]
    if any(h in first for h in ("service", "number", "phone", "mobile")):
        start = 1

    data_rows = raw_rows[start:]
    if not data_rows:
        return [], "empty"

    # Detect mode by column count of the majority of rows
    two_col_count = sum(1 for r in data_rows if len(r) >= 2)
    one_col_count = len(data_rows) - two_col_count

    if two_col_count > one_col_count:
        result = []
        for r in data_rows:
            if len(r) < 2:
                continue
            col0, col1 = r[0], r[1]
            # Determine which column is service and which is number
            col0_is_num = re.match(r"^\+?\d{6,15}$", re.sub(r"\s", "", col0))
            col1_is_num = re.match(r"^\+?\d{6,15}$", re.sub(r"\s", "", col1))
            if col0_is_num and not col1_is_num:
                svc = col1.lower().strip()
                num = re.sub(r"\D", "", col0)
            elif col1_is_num and not col0_is_num:
                svc = col0.lower().strip()
                num = re.sub(r"\D", "", col1)
            else:
                svc = col0.lower().strip()
                num = re.sub(r"\D", "", col1)
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


def _add_numbers_bulk(svc: str, numbers: list):
    """Add a list of number strings to stock[svc]. Returns (added, skipped)."""
    added, skipped = 0, 0
    svc = svc.lower().strip()
    if svc not in stock:
        return 0, len(numbers)
    for num in numbers:
        num = re.sub(r"\D", "", str(num))
        if not num:
            skipped += 1
            continue
        c_name, _ = get_country_details(num)
        if c_name == "Unknown":
            skipped += 1
            continue
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


@bot.message_handler(content_types=["document"])
def document_handler(message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return
    register_user(message.chat.id)

    doc = message.document
    name = doc.file_name or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    if ext not in ("xlsx", "xls", "csv"):
        bot.send_message(
            message.chat.id,
            "❌ <b>Unsupported file!</b>\n\n"
            "📎 Supported formats:\n"
            "  • <b>.xlsx</b> — Excel (new)\n"
            "  • <b>.xls</b>  — Excel (old)\n"
            "  • <b>.csv</b>  — CSV\n\n"
            "💡 File pathao abar!",
            parse_mode="HTML",
        )
        return

    wait = bot.send_message(
        message.chat.id, f"⏳🔥 <b>{name}</b> parse korchi...", parse_mode="HTML"
    )

    try:
        file_info = bot.get_file(doc.file_id)
        raw = bot.download_file(file_info.file_path)
    except Exception as e:
        bot.edit_message_text(
            f"❌ File download hoyni: {e}",
            message.chat.id,
            wait.message_id,
            parse_mode="HTML",
        )
        return

    rows, mode = _parse_spreadsheet(raw, name)

    try:
        bot.delete_message(message.chat.id, wait.message_id)
    except Exception:
        pass

    if mode in ("unknown", "empty") or not rows:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>File-e kono data paini!</b> ⚠️\n\n"
            "📋 <b>Supported formats:</b>\n"
            "  • <b>2-column:</b>  Service | Number\n"
            "  • <b>1-column:</b>  Number only (service pore dao)\n\n"
            "💡 Sample format:\n"
            "<code>facebook  | 8801700123456\n"
            "whatsapp  | 8801800234567\n"
            "telegram  | 251912345678</code>",
            parse_mode="HTML",
        )
        return

    if mode == "two_col":
        # Group by service and add directly
        service_map = {}
        for svc, num in rows:
            service_map.setdefault(svc, []).append(num)

        total_added, total_skipped = 0, 0
        report_lines = ""
        for svc, nums in service_map.items():
            added, skipped = _add_numbers_bulk(svc, nums)
            total_added += added
            total_skipped += skipped
            icon = "✅" if added else "⚠️"
            report_lines += f"{icon} <b>{svc.upper()}</b>: +{added} added"
            if skipped:
                report_lines += f"  (⚠️ {skipped} skip)"
            report_lines += "\n"

        bot.send_message(
            message.chat.id,
            f"📊🔥 <b>EXCEL IMPORT DONE!</b> 🔥📊\n"
            f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
            f"📎 <b>File:</b> <code>{name}</code>\n"
            f"📋 <b>Rows parsed:</b> {len(rows)}\n\n"
            f"{report_lines}\n"
            f"✅ <b>Total added:</b> {total_added}\n"
            f"⚠️ <b>Skipped:</b> {total_skipped}\n\n"
            f"⚡━━━━━━━━━━━━━━━━⚡\n"
            f"💡 /panels diye stock check koro.",
            reply_markup=main_menu(uid),
            parse_mode="HTML",
        )

    else:
        # one_col: ask which service
        _pending_excel[uid] = {"numbers": rows, "filename": name}
        bot.send_message(
            message.chat.id,
            f"📂🔥 <b>FILE LOADED!</b> 🔥📂\n"
            f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
            f"📎 <b>File:</b> <code>{name}</code>\n"
            f"📱 <b>Numbers found:</b> {len(rows)}\n\n"
            f" <b>Kon service-e add korbo?</b>\n"
            f"⬇️ Choose koro:",
            reply_markup=_service_select_markup(),
            parse_mode="HTML",
        )
        msg = bot.send_message(
            message.chat.id, "⬇️ Service type koro:", parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, _excel_pick_service)


def _excel_pick_service(message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return
    svc_raw = (message.text or "").strip().lower()
    # normalise common aliases
    svc_map = {
        "facebook": "facebook",
        "fb": "facebook",
        "instagram": "instagram",
        "ig": "instagram",
        "whatsapp": "whatsapp",
        "wa": "whatsapp",
        "telegram": "telegram",
        "tg": "telegram",
        "binance": "binance",
        "bnb": "binance",
        "pc clone": "pc clone",
        "pc": "pc clone",
        "clone": "pc clone",
    }
    svc = svc_map.get(svc_raw)
    if svc is None:
        # try direct match
        for s in VALID_SERVICES:
            if svc_raw == s:
                svc = s
                break
    if svc is None:
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid service choose koro:\n"
            "<code>Facebook / Instagram / WhatsApp / Telegram / Binance / PC Clone</code>",
            reply_markup=_service_select_markup(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _excel_pick_service)
        return

    pending = _pending_excel.pop(uid, None)
    if not pending:
        bot.send_message(
            message.chat.id,
            "⚠️ Session expired. File abar pathao.",
            reply_markup=main_menu(uid),
        )
        return

    numbers = pending["numbers"]
    filename = pending["filename"]
    added, skipped = _add_numbers_bulk(svc, numbers)

    bot.send_message(
        message.chat.id,
        f"📊🔥 <b>EXCEL IMPORT DONE!</b> 🔥📊\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"📎 <b>File:</b>     <code>{filename}</code>\n"
        f"💬 <b>Service:</b>  <b>{svc.upper()}</b>\n"
        f"📱 <b>Parsed:</b>   {len(numbers)}\n\n"
        f"✅ <b>Added:</b>    {added}\n"
        f"⚠️ <b>Skipped:</b>  {skipped}\n\n"
        f"⚡━━━━━━━━━━━━━━━━⚡\n"
        f"💡 /panels diye stock check koro.",
        reply_markup=main_menu(uid),
        parse_mode="HTML",
    )


@bot.message_handler(func=lambda m: True)
def text_handler(message):
    global stock
    uid = message.from_user.id
    txt = message.text
    register_user(message.chat.id)

    if txt == "☎️ 𝗡𝗨𝗠𝗕𝗔𝗥 ☎️":
        show_services(message)

    elif txt in _get_svc_map():
        svc = _get_svc_map()[txt]
        show_countries(message.chat.id, svc)

    elif txt == "🔙 Main Menu":
        mname = message.from_user.first_name or message.from_user.username or "User"
        bot.send_message(
            message.chat.id,
            f"╔═════════════════════╗\n"
            f"      USER MENU-te WELCOME!\n"
            f"   👋 <b>{mname}</b>, ki korte chao?\n"
            f"╚═════════════════════╝",
            reply_markup=main_menu(uid),
            parse_mode="HTML",
        )

    elif txt == "📞 𝗦𝗔𝗣𝗢𝗥𝗧":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📩 Support Team", url="https://t.me/Rabbi122q")
        )
        bot.send_message(
            message.chat.id,
            "📞 <b>SUPPORT</b> 📞\n"
            "⚡━━━━━━━━━━━━━━⚡\n\n"
            "Kono somossa hole nicher button e click koro!\n\n"
            "⚡━━━━━━━━━━━━━━⚡",
            reply_markup=markup,
            parse_mode="HTML",
        )

    elif txt == "📊 𝗦𝗧𝗢𝗖𝗞":
        report = "🔥 <b>LIVE STOCK REPORT</b> 🔥\n⚡━━━━━━━━━━━━⚡\n\n"
        for s, d in stock.items():
            total = sum(len(v) for v in d.values())
            report += f" <b>{s.upper()}</b>: {total} টি \n"
        report += "\n⚡━━━━━━━━━━━━⚡\n🤖 <b>AR OTP BOT</b> 🔥"
        bot.send_message(message.chat.id, report, parse_mode="HTML")

    elif txt == "⚙️ 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 ⚙️" and uid in ADMIN_IDS:
        _go_admin_panel(message)

    elif txt == "🔥📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁" and uid in ADMIN_IDS:
        msg = bot.send_message(
            message.chat.id,
            "✍️ <b>Broadcast content পাঠাও:</b> \n\n"
            "📝 Text, 🖼️ Photo, 🎥 Video, or 🎭 Sticker (with optional caption) — সব accept হবে!\n\n"
            "🔙 Back jete <b>Admin Panel</b> button press koro.",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, do_broadcast)

    elif txt == "⚡👥 𝗨𝘀𝗲𝗿 𝗖𝗼𝘂𝗻𝘁" and uid in ADMIN_IDS:
        bot.send_message(
            message.chat.id,
            f" <b>TOTAL USERS</b> \n\n⚡ <b>{len(users)}</b> জন আছে! 🔥",
            parse_mode="HTML",
        )

    elif txt == "📋👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁" and uid in ADMIN_IDS:
        all_ids = list(users)
        total = len(all_ids)
        if total == 0:
            bot.send_message(message.chat.id, "📋 No users yet.", parse_mode="HTML")
        else:
            bot.send_message(
                message.chat.id, "⏳ Loading user names...", parse_mode="HTML"
            )
            updated = False
            for user_id in all_ids:
                key = str(user_id)
                existing = user_names.get(key, "")
                if existing and not existing.strip().lstrip("-").isdigit():
                    continue
                try:
                    chat_info = bot.get_chat(user_id)
                    full = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".strip()
                    uname = chat_info.username or ""
                    if full and uname:
                        display = f"{full} (@{uname})"
                    elif full:
                        display = full
                    elif uname:
                        display = f"@{uname}"
                    else:
                        display = None
                    if display:
                        user_names[key] = display
                        updated = True
                except Exception:
                    pass
            if updated:
                save_json(USER_NAMES_FILE, user_names)

            PAGE = 50
            chunks = [all_ids[i : i + PAGE] for i in range(0, total, PAGE)]
            for idx, chunk in enumerate(chunks):
                lines = (
                    f"📋👥 <b>USER LIST</b> 👥📋\n"
                    f"⚡━━━━━━━━━━━━━━━━⚡\n"
                    f"📊 Total: <b>{total}</b> users"
                    + (f"  |  Page {idx + 1}/{len(chunks)}" if len(chunks) > 1 else "")
                    + "\n⚡━━━━━━━━━━━━━━━━⚡\n\n"
                )
                for i, user_id in enumerate(chunk, start=idx * PAGE + 1):
                    name = user_names.get(str(user_id), "—")
                    lines += f"{i}. 🆔 <code>{user_id}</code>\n    👤 {name}\n\n"
                bot.send_message(message.chat.id, lines, parse_mode="HTML")

    elif txt == "➕ 𝗡𝘂𝗺𝗯𝗮𝗿 𝗔𝗱𝗱" and uid in ADMIN_IDS:
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("facebook", "instagram", "whatsapp", "telegram", "binance", "pc clone")
        m.add("❌ Cancel")
        msg = bot.send_message(
            message.chat.id,
            "🔥 <b>Service choose koro:</b> 🔥",
            reply_markup=m,
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, process_auto_add)

    elif txt == "🗑️ 𝗦𝗼𝗯 𝗖𝗹𝗲𝗮𝗿" and uid in ADMIN_IDS:
        bot.send_message(
            message.chat.id,
            "🗑️🔥 <b>STOCK CLEAR PANEL</b> 🔥🗑️\n\n"
            " <b>Kon service-er stock clear korbe?</b>\n"
            "⬇️ Service choose koro:",
            reply_markup=_clr_service_markup(),
            parse_mode="HTML",
        )

    elif txt == "🎭 𝗗𝗘𝗠𝗢 𝗢𝗧𝗣" and uid in ADMIN_IDS:
        bot.send_message(
            message.chat.id,
            demo_status_text(),
            reply_markup=demo_menu_markup(),
            parse_mode="HTML",
        )
        with _demo_lock:
            has_configs = len(_demo_configs) > 0
        if has_configs:
            bot.send_message(
                message.chat.id,
                "⚡ <b>Config Start/Stop:</b>",
                reply_markup=demo_cfg_inline_markup(),
                parse_mode="HTML",
            )

    elif txt == "➕ 𝗔𝗱𝗱 𝗣𝗮𝗻𝗲𝗹" and uid in ADMIN_IDS:
        _addpanel_state[uid] = {"step": "url", "data": {}}
        msg = bot.send_message(
            message.chat.id,
            "🔧🔥 <b>ADD NEW PANEL</b> 🔥🔧\n\n"
            "📡 <b>Step 1/3:</b> Panel URL pathao\n\n"
            "Supported formats:\n"
            "• <code>http://1.2.3.4/ints/agent/SMSCDRStats</code>\n"
            "• <code>https://truesms.net/agent/SMSCDRStats</code>\n"
            "• <code>https://truesms.net/agent/SMSRanges</code>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _ap_get_url)

    elif txt == "➕ 𝗔𝗱𝗱 𝗦𝗲𝗿𝘃𝗶𝗰𝗲" and uid in ADMIN_IDS:
        _addservice_state[uid] = {}
        msg = bot.send_message(
            message.chat.id,
            "📋🔥 <b>ADD NEW SERVICE</b> 🔥📋\n\n"
            "🏷️ <b>Step 1/2:</b> Button-e ki lekha thakbe?\n"
            "<i>Example: Telegram 🔵, Binance 💛, TikTok 🎵</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _svc_get_label)

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗦𝗲𝗿𝘃𝗶𝗰𝗲" and uid in ADMIN_IDS:
        if not _services:
            bot.send_message(message.chat.id, "📋 Kono service nai!", parse_mode="HTML")
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for s in _services:
                markup.add(types.InlineKeyboardButton(
                    f"🗑️ {s['label']}  [{s['key']}]",
                    callback_data=f"rmsvc:{s['key']}",
                ))
            bot.send_message(
                message.chat.id,
                "🗑️🔥 <b>REMOVE SERVICE</b>\n\nKon service remove korbe?",
                reply_markup=markup,
                parse_mode="HTML",
            )

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗮𝗻𝗲𝗹" and uid in ADMIN_IDS:
        if not _dynamic_panels:
            bot.send_message(
                message.chat.id,
                "📋 <b>Kono dynamic panel nai!</b>\n💡 Add Panel button diye add koro.",
                parse_mode="HTML",
            )
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p in _dynamic_panels:
                pid = p["id"]
                with _stats_lock:
                    s = _panel_stats.get(pid, {})
                st = s.get("status", "⏳")
                markup.add(
                    types.InlineKeyboardButton(
                        f"{st} {p.get('username','?')} — {p.get('host','?')}",
                        callback_data=f"rmpanel:{pid}",
                    )
                )
            bot.send_message(
                message.chat.id,
                "🗑️🔥 <b>REMOVE PANEL</b>\n\nKon panel remove korbe?",
                reply_markup=markup,
                parse_mode="HTML",
            )


    elif txt == "➕ 𝗖𝗼𝗻𝗳𝗶𝗴 𝗬𝗼𝗴 𝗞𝗼𝗿𝗼" and uid in ADMIN_IDS:
        _demo_cfg_temp[uid] = {}
        msg = bot.send_message(
            message.chat.id,
            "📱 <b>Phone number(s) dao:</b>\n\n"
            "• Ekta number: <code>8801700123456</code>\n"
            "• Multiple (newline or comma):\n"
            "<code>8801700123456\n251912345678\n2348012345678</code>\n\n"
            "⚠️ Full country code including number lagbe!",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _demo_cfg_number)

    elif txt == "🗑️ 𝗖𝗼𝗻𝗳𝗶𝗴 𝗠𝘂𝗰𝗵𝗼" and uid in ADMIN_IDS:
        with _demo_lock:
            configs = list(_demo_configs)
        if not configs:
            bot.send_message(
                message.chat.id,
                "📋 <b>Kono config nai!</b>",
                reply_markup=demo_menu_markup(),
                parse_mode="HTML",
            )
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for cfg in configs:
                svcs = ", ".join(cfg.get("services") or ["?"])
                markup.add(types.InlineKeyboardButton(
                    f"🗑️ {cfg['name']}  [{svcs}  |  {cfg['interval']}s]",
                    callback_data=f"rmcfg:{cfg['id']}",
                ))
            bot.send_message(
                message.chat.id,
                "🗑️🔥 <b>Config মুছো</b>\n\nকোন config মুছবে?",
                reply_markup=markup,
                parse_mode="HTML",
            )

    elif txt == "📊 𝗣𝗮𝗻𝗲𝗹𝘀" and uid in ADMIN_IDS:
        panels_cmd(message)

    elif txt == "👑 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻" and uid in ADMIN_IDS:
        msg = bot.send_message(
            message.chat.id,
            "👑 <b>New Admin add</b>\n\n"
            "Notun admin-er Telegram <b>User ID</b> dao:\n"
            "<i>Example: 123456789</i>\n\n"
            "💡 User ID jante hole sei user-ke @userinfobot-e forward koro.",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _admin_add_get_id)

    elif txt == "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻" and uid in ADMIN_IDS:
        _show_remove_admin(message)

    elif txt == "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀" and uid in ADMIN_IDS:
        _show_settings(message)

    elif txt == "✏️ 𝗘𝗱𝗶𝘁 𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀" and uid in ADMIN_IDS:
        _show_edit_messages_menu(message)

    elif txt in ("🔙 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟", "🔙 Admin Panel") and uid in ADMIN_IDS:
        _go_admin_panel(message)

    elif txt == "⬅️🔙 𝗨𝘀𝗲𝗿 𝗠𝗲𝗻𝘂":
        mname = message.from_user.first_name or message.from_user.username or "User"
        bot.send_message(
            message.chat.id,
            f"╔═════════════════════╗\n"
            f"      USER MENU-te WELCOME!\n"
            f"   👋 <b>{mname}</b>, ki korte chao?\n"
            f"╚═════════════════════╝",
            reply_markup=main_menu(uid),
            parse_mode="HTML",
        )


# ── Demo OTP config step handlers ─────────────────────────────────────────────


def _demo_cfg_number(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    raw_lines = re.split(r"[\n,]+", message.text or "")
    candidates = [re.sub(r"\D", "", ln) for ln in raw_lines if re.sub(r"\D", "", ln)]
    if not candidates:
        msg = bot.send_message(
            message.chat.id,
            "❌ Kono number paini. Ekta ba multiple number dao:",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _demo_cfg_number)
        return
    valid, invalid = [], []
    result_lines = ""
    for num in candidates:
        if len(num) < 7:
            invalid.append(num)
            continue
        c_name, flag = get_country_details(num)
        if c_name == "Unknown":
            invalid.append(num)
        else:
            valid.append(num)
            result_lines += f"  ✅ <code>{num}</code>  {flag} {c_name}\n"
    if not valid:
        msg = bot.send_message(
            message.chat.id,
            f"⚠️ <b>Kono valid number paini!</b>\n\n"
            f"Full international number dao (country code including):\n"
            f"🇧🇩 Bangladesh → <code>8801700123456</code>\n"
            f"🇪🇹 Ethiopia   → <code>251912345678</code>\n"
            f"🇳🇬 Nigeria    → <code>2348012345678</code>\n\n"
            f"Aro ekbar try koro:",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _demo_cfg_number)
        return
    uid = message.from_user.id
    _demo_cfg_temp.setdefault(uid, {})["numbers"] = valid
    SHOW_MAX = 10
    shown = result_lines.split("\n")[:SHOW_MAX]
    preview = "\n".join(shown)
    if len(valid) > SHOW_MAX:
        preview += f"\n  ... +{len(valid) - SHOW_MAX} more"
    feedback = f"✅ <b>{len(valid)} টি number set hoiche:</b>\n{preview}\n"
    if invalid:
        inv_preview = invalid[:5]
        feedback += (
            f"\n⚠️ Skip (invalid): {', '.join(f'<code>{x}</code>' for x in inv_preview)}"
        )
        if len(invalid) > 5:
            feedback += f" +{len(invalid) - 5} more"
        feedback += "\n"
    svc_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    svc_markup.add("4", "5", "6", "7", "8")
    svc_markup.add("🔙 Admin Panel")
    msg = bot.send_message(
        message.chat.id,
        feedback + "\n🔢 <b>OTP digit count choose koro:</b>",
        reply_markup=svc_markup,
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _demo_cfg_digits)


def _demo_cfg_digits(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    try:
        d = int(message.text.strip())
        if d < 4 or d > 8:
            raise ValueError
    except ValueError:
        svc_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        svc_markup.add("4", "5", "6", "7", "8")
        svc_markup.add("🔙 Admin Panel")
        msg = bot.send_message(message.chat.id, "❌ 4 theke 8 er modhye number dao:", reply_markup=svc_markup)
        bot.register_next_step_handler(msg, _demo_cfg_digits)
        return
    uid = message.from_user.id
    _demo_cfg_temp.setdefault(uid, {})["digits"] = d
    _demo_svc_state[uid] = []
    _demo_cfg_service_ask(message)


def _demo_cfg_service_ask(message):
    uid = message.from_user.id
    current = _demo_svc_state.get(uid, [])
    svc_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    svc_markup.add("Facebook", "Instagram", "WhatsApp")
    svc_markup.add("Telegram", "PC Clone", "Twitter")
    svc_markup.add("Tiktok", "Snapchat", "Gmail")
    if current:
        svc_markup.add("✅ হয়েছে (Done)")
    svc_markup.add("🔙 Admin Panel")
    if current:
        svc_list = "\n".join(f"  ✅ {s}" for s in current)
        prompt = (
            f"✅ <b>Selected services ({len(current)}):</b>\n{svc_list}\n\n"
            f"➕ <b>আরো service যোগ করো</b> অথবা <b>✅ হয়েছে</b> চাপো:"
        )
    else:
        prompt = (
            "💬 <b>Service choose koro</b>\n\n"
            "<i>একাধিক service add করা যাবে — সব শেষে '✅ হয়েছে' চাপো।</i>"
        )
    msg = bot.send_message(message.chat.id, prompt, reply_markup=svc_markup, parse_mode="HTML")
    bot.register_next_step_handler(msg, _demo_cfg_service_multi)


def _demo_cfg_service_multi(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    uid = message.from_user.id
    txt = (message.text or "").strip()

    if txt in ("✅ হয়েছে (Done)", "✅ হয়েছে"):
        svcs = _demo_svc_state.get(uid, [])
        if not svcs:
            bot.send_message(
                message.chat.id,
                "⚠️ <b>কমপক্ষে একটা service select করো!</b>",
                parse_mode="HTML",
            )
            _demo_cfg_service_ask(message)
            return
        uid2 = message.from_user.id
        _demo_cfg_temp.setdefault(uid2, {})["services"] = svcs
        intvl_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
        intvl_markup.add("5", "10", "15", "30", "60", "120", "300")
        intvl_markup.add("🔙 Admin Panel")
        svc_list = ", ".join(svcs)
        msg = bot.send_message(
            message.chat.id,
            f"✅ <b>Services set:</b> {svc_list}\n\n⏱️ <b>Interval (seconds) dao:</b>",
            reply_markup=intvl_markup,
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _demo_cfg_interval)
        return

    if not txt:
        _demo_cfg_service_ask(message)
        return

    current = _demo_svc_state.setdefault(uid, [])
    if txt in current:
        bot.send_message(
            message.chat.id,
            f"⚠️ <b>{txt}</b> already added আছে! আরো যোগ করো বা <b>✅ হয়েছে</b> চাপো।",
            parse_mode="HTML",
        )
    else:
        current.append(txt)
    _demo_cfg_service_ask(message)


def _demo_cfg_interval(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    try:
        iv = int(message.text.strip())
        if iv < 5:
            raise ValueError
    except ValueError:
        intvl_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
        intvl_markup.add("5", "10", "15", "30", "60", "120", "300")
        intvl_markup.add("🔙 Admin Panel")
        msg = bot.send_message(message.chat.id, "❌ Minimum 5 second. Aro dao:", reply_markup=intvl_markup)
        bot.register_next_step_handler(msg, _demo_cfg_interval)
        return
    global _demo_cfg_id_counter
    uid = message.from_user.id
    tmp = _demo_cfg_temp.pop(uid, {})
    numbers = tmp.get("numbers", ["8801700000000"])
    digits = tmp.get("digits", 6)
    services = tmp.get("services", ["Facebook"])
    with _demo_lock:
        _demo_cfg_id_counter += 1
        cid = _demo_cfg_id_counter
        cfg_name = f"Config {cid}"
        _demo_configs.append({
            "id": cid,
            "name": cfg_name,
            "active": False,
            "numbers": numbers,
            "digits": digits,
            "services": services,
            "interval": iv,
        })
    svcs_str = ", ".join(services)
    bot.send_message(
        message.chat.id,
        f"✅🔥 <b>{cfg_name} যোগ হয়েছে!</b>\n\n"
        f"  📱 Numbers: {len(numbers)} টি\n"
        f"  🔢 Digits: {digits}\n"
        f"  💬 Services: {svcs_str}\n"
        f"  ⏱️ Interval: {iv}s\n\n"
        + demo_status_text(),
        reply_markup=demo_menu_markup(),
        parse_mode="HTML",
    )


def make_broadcast_msg(text):
    return (
        "🔥 <b>𝗔𝗥 𝗢𝗧𝗣 𝗕𝗢𝗧 — 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧!</b> 🔥\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n\n"
        f"📢 {text} 📢\n\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n"
        "🤖🔥 <i>𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝙗𝙮</i>  <b>𝗔𝗥 𝗢𝗧𝗣 𝗕𝗢𝗧</b>  🔥🤖"
    )


def do_broadcast(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    has_text = bool(message.text)
    has_photo = bool(message.photo)
    has_video = bool(message.video)
    has_sticker = bool(message.sticker)
    has_animation = bool(message.animation)
    has_audio = bool(message.audio)
    has_voice = bool(message.voice)
    has_document = bool(message.document)
    has_video_note = bool(message.video_note)

    if not any(
        [
            has_text,
            has_photo,
            has_video,
            has_sticker,
            has_animation,
            has_audio,
            has_voice,
            has_document,
            has_video_note,
        ]
    ):
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Kono content paoa jaini!</b> ⚠️\n"
            "Text, Photo, Video, GIF, Audio, Voice, Document ba Sticker pathao.",
            parse_mode="HTML",
        )
        return

    cap = (
        lambda m: make_broadcast_msg(m.caption) if m.caption else make_broadcast_msg("")
    )

    bot.send_message(
        message.chat.id,
        f"⏳🔥 <b>{len(users)} জনকে পাঠানো হচ্ছে...</b> 🔥⏳",
        parse_mode="HTML",
    )

    success, fail = 0, 0
    for uid in list(users):
        try:
            if has_photo:
                bot.send_photo(
                    uid,
                    message.photo[-1].file_id,
                    caption=cap(message),
                    parse_mode="HTML",
                )
            elif has_animation:
                bot.send_animation(
                    uid,
                    message.animation.file_id,
                    caption=cap(message),
                    parse_mode="HTML",
                )
            elif has_video:
                bot.send_video(
                    uid, message.video.file_id, caption=cap(message), parse_mode="HTML"
                )
            elif has_video_note:
                bot.send_video_note(uid, message.video_note.file_id)
            elif has_sticker:
                bot.send_sticker(uid, message.sticker.file_id)
            elif has_audio:
                bot.send_audio(
                    uid, message.audio.file_id, caption=cap(message), parse_mode="HTML"
                )
            elif has_voice:
                bot.send_voice(
                    uid, message.voice.file_id, caption=cap(message), parse_mode="HTML"
                )
            elif has_document:
                bot.send_document(
                    uid,
                    message.document.file_id,
                    caption=cap(message),
                    parse_mode="HTML",
                )
            else:
                bot.send_message(
                    uid, make_broadcast_msg(message.text), parse_mode="HTML"
                )
            success += 1
        except Exception:
            fail += 1

    bot.send_message(
        message.chat.id,
        f" <b>BROADCAST COMPLETE!</b> \n\n"
        f"✅ <b>𝗦𝗼𝗳𝗼𝗹:</b> {success} জন 🔥\n"
        f"❌ <b>𝗕𝗮𝗿𝘁𝗵𝗼:</b> {fail} জন ",
        reply_markup=main_menu(message.from_user.id),
        parse_mode="HTML",
    )


_pending_add = {}


def _start_countdown(chat_id, msg_id, svc, flag, c_name, display_num, scnt):
    if chat_id in _countdowns:
        _countdowns[chat_id].set()
    cancel = threading.Event()
    _countdowns[chat_id] = cancel

    def run():
        total = 600
        while not cancel.is_set():
            mins = total // 60
            secs = total % 60
            text = (
                f"✅ <b>Number Assigned Successfully !</b>\n\n"
                f"🔧 <b>Platform :</b> {svc.capitalize()}\n"
                f"🌍 <b>Country :</b> {flag} {c_name}\n\n"
                f"📞 <b>Number :</b> <code>{display_num}</code>\n\n"
                f"⏱ <b>Auto code fetch :</b> {mins:02d}:{secs:02d}s"
            )
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🔄 New Number", callback_data=f"n:{svc}:{scnt}"),
                types.InlineKeyboardButton("🌍 Change Country", callback_data=f"s:{svc}"),
            )
            kb.add(
                types.InlineKeyboardButton("📢 OTP Group", url=get_otp_group_link()),
            )
            try:
                bot.edit_message_text(
                    text, chat_id, msg_id,
                    reply_markup=kb, parse_mode="HTML",
                )
            except Exception:
                pass
            cancel.wait(5)
            if cancel.is_set():
                break
            total -= 5
            if total < 0:
                total = 600

    threading.Thread(target=run, daemon=True).start()


def _settings_text():
    grp_id = _group_settings.get("otp_group_id")
    grp_link = _group_settings.get("otp_group_link", "")
    auto_del = _group_settings.get("auto_delete", True)
    del_secs = _group_settings.get("auto_delete_seconds", 3600)
    ch2 = _group_settings.get("channel2", "")
    bot_lnk = _group_settings.get("bot_link", "")
    id_str = f"<code>{grp_id}</code>" if grp_id else "❌ Set hoy nai"
    link_str = grp_link or "❌ Set hoy nai"
    auto_str = f"🟢 ON ({del_secs // 60} min)" if auto_del else "🔴 OFF"
    ch2_str = ch2 or "❌ Set hoy nai"
    bot_str = bot_lnk or "❌ Set hoy nai"
    return (
        "⚙️ <b>BOT SETTINGS</b> ⚙️\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n\n"
        "📡 <b>OTP GROUP</b>\n"
        f"🔗 Link: {link_str}\n"
        f"🆔 Chat ID: {id_str}\n"
        f"⏱️ Auto Delete: {auto_str}\n\n"
        "📢 <b>LINKS</b>\n"
        f"📢 Join Channel: {ch2_str}\n"
        f"🤖 Bot Link: {bot_str}\n\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n"
        "⬇️ Ki change korte chao?"
    )


def _settings_markup():
    auto_del = _group_settings.get("auto_delete", True)
    auto_label = "⏱️ Auto Delete: 🟢 ON" if auto_del else "⏱️ Auto Delete: 🔴 OFF"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Group Link", callback_data="grp_setlink"),
        types.InlineKeyboardButton("🆔 Group Chat ID", callback_data="grp_setid"),
    )
    markup.add(
        types.InlineKeyboardButton(auto_label, callback_data="set_autodel"),
        types.InlineKeyboardButton("🗑️ Remove Group", callback_data="grp_remove"),
    )
    markup.add(
        types.InlineKeyboardButton("📢 Join Channel", callback_data="set_channel2"),
        types.InlineKeyboardButton("🤖 Bot Link", callback_data="set_botlink"),
    )
    return markup


def _show_settings(message):
    bot.send_message(
        message.chat.id,
        _settings_text(),
        reply_markup=_settings_markup(),
        parse_mode="HTML",
    )


def _show_settings_inline(call):
    try:
        bot.edit_message_text(
            _settings_text(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=_settings_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass


def _show_group_settings(message):
    _show_settings(message)


def _show_group_settings_inline(call):
    _show_settings_inline(call)


def _grp_get_link(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    link = (message.text or "").strip()
    if not link.startswith("https://t.me/") and not link.startswith("http://"):
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid Telegram link dao:\n<i>Example: https://t.me/aR_OTP_rcv</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _grp_get_link)
        return
    _group_settings["otp_group_link"] = link
    save_group_settings()
    _go_admin_panel(
        message,
        f"✅🔥 <b>GROUP LINK UPDATED!</b>\n\n"
        f"🔗 <b>Notun Link:</b> {link}\n\n"
        f"<i>Ekhon theke number-er nichor OTP Group button-e ei link thakbe.</i>",
    )


def _grp_get_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    raw = (message.text or "").strip()
    try:
        gid = int(raw)
    except ValueError:
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid Chat ID dao (number):\n<i>Example: -1001234567890</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _grp_get_id)
        return
    _group_settings["otp_group_id"] = gid
    save_group_settings()
    _go_admin_panel(
        message,
        f"✅🔥 <b>GROUP CHAT ID UPDATED!</b>\n\n"
        f"🆔 <b>Notun Chat ID:</b> <code>{gid}</code>\n\n"
        f"<i>Ekhon theke OTP ei group-e pathano hobe.</i>",
    )


def _sett_get_channel2(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    link = (message.text or "").strip()
    if not link.startswith("https://") and not link.startswith("http://"):
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid link dao:\n<i>Example: https://t.me/aR_OTP_rcv</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _sett_get_channel2)
        return
    _group_settings["channel2"] = link
    save_group_settings()
    _go_admin_panel(
        message,
        f"✅ <b>JOIN CHANNEL UPDATED!</b>\n\n"
        f"📢 <b>Notun Link:</b> {link}",
    )


def _sett_get_botlink(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    link = (message.text or "").strip()
    if not link.startswith("https://") and not link.startswith("http://"):
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid link dao:\n<i>Example: https://t.me/ar_otp_bot</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _sett_get_botlink)
        return
    _group_settings["bot_link"] = link
    save_group_settings()
    _go_admin_panel(
        message,
        f"✅ <b>BOT LINK UPDATED!</b>\n\n"
        f"🤖 <b>Notun Link:</b> {link}",
    )


def _admin_add_get_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    raw = (message.text or "").strip()
    try:
        new_uid = int(raw)
    except ValueError:
        msg = bot.send_message(
            message.chat.id,
            "❌ Valid Telegram User ID dao (shudhu number):\n<i>Example: 123456789</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _admin_add_get_id)
        return
    if add_admin(new_uid):
        _go_admin_panel(
            message,
            f"✅ <b>ADMIN ADDED!</b>\n\n"
            f"👑 <b>New Admin ID:</b> <code>{new_uid}</code>\n\n"
            f"<i>Ekhon theke ei user admin panel access pabe.</i>",
        )
    else:
        _go_admin_panel(
            message,
            f"⚠️ <b>User <code>{new_uid}</code> already admin ache!</b>",
        )


def _show_remove_admin(message):
    removable = [a for a in ADMIN_IDS if a != SUPER_ADMIN_ID]
    if not removable:
        bot.send_message(
            message.chat.id,
            "ℹ️ <b>Remove korar moto kono extra admin nei.</b>\n\n"
            "<i>Super Admin remove kora jabe na.</i>",
            reply_markup=_back_admin_kb(),
            parse_mode="HTML",
        )
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for aid in removable:
        name = user_names.get(str(aid), {}).get("first_name", "") or str(aid)
        markup.add(types.InlineKeyboardButton(
            f"🗑️ {name} [{aid}]", callback_data=f"rmadmin:{aid}"
        ))
    bot.send_message(
        message.chat.id,
        "🗑️ <b>Remove Admin</b>\n\n"
        "⚡━━━━━━━━━━━━━━━━⚡\n"
        "Niche theke admin select koro:\n\n"
        "<i>⚠️ Super Admin remove kora jabe na.</i>",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _go_admin_panel(message, text="🔥 <b>ADMIN PANEL</b>"):
    m_admin = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m_admin.add("➕ 𝗡𝘂𝗺𝗯𝗮𝗿 𝗔𝗱𝗱", "🗑️ 𝗦𝗼𝗯 𝗖𝗹𝗲𝗮𝗿")
    m_admin.add("🔥📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", "⚡👥 𝗨𝘀𝗲𝗿 𝗖𝗼𝘂𝗻𝘁")
    m_admin.add("📋👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁")
    m_admin.add("🎭 𝗗𝗘𝗠𝗢 𝗢𝗧𝗣")
    m_admin.add("➕ 𝗔𝗱𝗱 𝗣𝗮𝗻𝗲𝗹", "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗮𝗻𝗲𝗹")
    m_admin.add("➕ 𝗔𝗱𝗱 𝗦𝗲𝗿𝘃𝗶𝗰𝗲", "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗦𝗲𝗿𝘃𝗶𝗰𝗲")
    m_admin.add("📊 𝗣𝗮𝗻𝗲𝗹𝘀")
    m_admin.add("👑 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻", "🗑️ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻")
    m_admin.add("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")
    m_admin.add("✏️ 𝗘𝗱𝗶𝘁 𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀")
    m_admin.add("⬅️🔙 𝗨𝘀𝗲𝗿 𝗠𝗲𝗻𝘂")
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=m_admin,
        parse_mode="HTML",
    )


# ── Edit Message Templates ──────────────────────────────────────────────────────

def _show_edit_messages_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, label in _TEMPLATE_LABELS.items():
        markup.add(types.InlineKeyboardButton(label, callback_data=f"editmsg:{key}"))
    markup.add(types.InlineKeyboardButton("🔄 সব Default এ Reset করো", callback_data="editmsg_reset_all"))
    bot.send_message(
        message.chat.id,
        "✏️🔥 <b>মেসেজ ফরমেট এডিট</b> 🔥✏️\n\n"
        "কোন মেসেজ এডিট করতে চাও সিলেক্ট করো:",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _ask_new_template(call, key):
    label = _TEMPLATE_LABELS.get(key, key)
    vars_hint = _TEMPLATE_VARS.get(key, "")
    current = get_template(key)
    uid = call.from_user.id
    _edit_template_state[uid] = {"key": key, "msg_id": call.message.message_id}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    msg = bot.send_message(
        call.message.chat.id,
        f"✏️ <b>{label}</b>\n\n"
        f"📌 <b>ব্যবহারযোগ্য ভেরিয়েবল:</b>\n<code>{vars_hint}</code>\n\n"
        f"📄 <b>বর্তমান ফরমেট:</b>\n<code>{current[:600]}</code>\n\n"
        f"⬇️ <b>নতুন ফরমেট লিখো:</b>\n"
        f"<i>(HTML ট্যাগ সাপোর্টেড: &lt;b&gt;, &lt;i&gt;, &lt;code&gt;, &lt;/b&gt; etc.)</i>",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _save_new_template)


def _save_new_template(message):
    uid = message.from_user.id
    if _is_back(message.text):
        _edit_template_state.pop(uid, None)
        _go_admin_panel(message)
        return
    state = _edit_template_state.pop(uid, None)
    if not state:
        _go_admin_panel(message)
        return
    key = state["key"]
    new_text = message.text or ""
    if not new_text.strip():
        msg = bot.send_message(
            message.chat.id,
            "❌ খালি রাখা যাবে না। আবার লিখো:",
            reply_markup=_back_admin_kb(),
        )
        _edit_template_state[uid] = state
        bot.register_next_step_handler(msg, _save_new_template)
        return
    _templates[key] = new_text
    save_templates()
    label = _TEMPLATE_LABELS.get(key, key)
    _go_admin_panel(
        message,
        f"✅🔥 <b>মেসেজ আপডেট হয়েছে!</b>\n\n"
        f"✏️ <b>{label}</b>\n\n"
        f"📄 নতুন ফরমেট সেভ হয়েছে।",
    )


def _cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Cancel")
    return kb


def _back_admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 Admin Panel")
    return kb


def _is_back(txt):
    return (txt or "").strip() in ("🔙 Admin Panel", "❌ Cancel")


def process_auto_add(message):
    svc = (message.text or "").strip().lower()
    if svc == "❌ cancel":
        _go_admin_panel(message)
        return
    if svc not in stock:
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("facebook", "instagram", "whatsapp", "telegram", "binance", "pc clone")
        m.add("❌ Cancel")
        msg = bot.send_message(
            message.chat.id,
            " <b>Vul service! Abar choose koro:</b>",
            reply_markup=m,
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, process_auto_add)
        return
    msg = bot.send_message(
        message.chat.id,
        f"🔥 <b>{svc.upper()}</b>\n\n"
        f"📝 <b>Slot name dao:</b>\n"
        f"<i>Udharan: Mali 1, Germany 2, India 3</i>",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, svc))


def ask_numbers_for_slot(message, svc):
    slot_name = (message.text or "").strip()
    if slot_name == "❌ Cancel":
        _go_admin_panel(message)
        return
    if not slot_name:
        msg = bot.send_message(
            message.chat.id,
            "❌ Slot name dao:",
            reply_markup=_cancel_kb(),
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, svc))
        return
    msg = bot.send_message(
        message.chat.id,
        f"✅ Slot: <b>{slot_name}</b>\n\n"
        f"📱 Ekhon <b>{svc.upper()}</b> er number gulo pathao:\n"
        f"<i>(Newline ba comma diye alag koro)</i>",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, lambda m: finalize_auto_add(m, svc, slot_name))


def finalize_auto_add(message, svc, slot_name=None):
    global stock
    uid = message.from_user.id
    if (message.text or "").strip() == "❌ Cancel":
        _go_admin_panel(message)
        return
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
    bot.send_message(
        message.chat.id,
        f"✅🔥 <b>DONE!</b>\n\n"
        f"🗂 <b>Slot:</b> {slot_name or 'Auto'}\n"
        f"📱 <b>Added:</b> {added_count} টি number",
        reply_markup=markup,
        parse_mode="HTML",
    )
    bot.register_next_step_handler(
        bot.send_message(message.chat.id, "⬇️ Ki korbe?", parse_mode="HTML"),
        lambda m: _after_add_handler(m, svc),
    )


def _after_add_handler(message, last_svc):
    txt = (message.text or "").strip()
    if txt == "➕ Aro Add koro":
        msg = bot.send_message(
            message.chat.id,
            f"📝 <b>Notun slot name dao:</b>\n<i>Udharan: Mali 2, Germany 3</i>",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, lambda m: ask_numbers_for_slot(m, last_svc))
    else:
        bot.send_message(
            message.chat.id,
            "🔙 Admin Menu",
            reply_markup=main_menu(message.from_user.id),
            parse_mode="HTML",
        )


# ── Heartbeat / watchdog ───────────────────────────────────────────────────────



# ── Start ─────────────────────────────────────────────────────────────────────

try:
    requests.get(
        f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook?drop_pending_updates=true",
        timeout=10,
    )
    print("[START] Webhook cleared.")
except Exception as e:
    print(f"[START] Webhook clear failed: {e}")

time.sleep(3)

threading.Thread(target=panel1_monitor, daemon=True).start()
threading.Thread(target=panel2_monitor, daemon=True).start()
threading.Thread(target=panel3_monitor, daemon=True).start()
threading.Thread(target=panel4_monitor, daemon=True).start()
threading.Thread(target=panel5_monitor, daemon=True).start()
threading.Thread(target=panel6_monitor, daemon=True).start()
threading.Thread(target=demo_monitor, daemon=True).start()

for _dp in _dynamic_panels:
    _start_dynamic_panel(_dp)
    print(f"[DYN] Loaded saved panel: {_dp['id']} ({_dp['host']})")

print("🔥 AR OTP BOT is running with 6-PANEL AUTO OTP MONITOR... 🔥")
print("   ▸ Panel 1: Mahofuza        (91.232.105.47)")
print("   ▸ Panel 2: Sagardas50      (94.23.31.29)")
print("   ▸ Panel 3: Rabbi1_FD       (168.119.13.175)")
print("   ▸ Panel 4: Rabbi12         (144.217.71.192)")
print("   ▸ Panel 5: Rabbi12_v2      (51.75.144.178)")
print("   ▸ Panel 6: TrueSMS/Ranges  (truesms.net)")


def _clear_webhook():
    try:
        requests.get(
            f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10,
        )
    except Exception:
        pass


while True:
    try:
        _clear_webhook()
        time.sleep(2)
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            allowed_updates=["message", "callback_query"],
        )
    except requests.exceptions.ReadTimeout:
        print("[POLLING] ReadTimeout — restarting in 3s...")
        time.sleep(3)
    except requests.exceptions.ConnectionError:
        print("[POLLING] ConnectionError — restarting in 5s...")
        time.sleep(5)
    except Exception as e:
        print(f"[POLLING] Error: {e} — restarting in 5s...")
        time.sleep(5)
