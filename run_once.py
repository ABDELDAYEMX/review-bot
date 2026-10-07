import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
BASE = Path(__file__).parent
VIDEOS_FILE = BASE / "videos.json"
STATE_FILE = BASE / "state.json"
CAIRO = ZoneInfo("Africa/Cairo")
API = f"https://api.telegram.org/bot{TOKEN}"


def call(method, **params):
    req = urllib.request.Request(
        f"{API}/{method}",
        data=json.dumps(params).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["result"]


def safe_call(method, **params):
    try:
        return call(method, **params)
    except urllib.error.HTTPError:
        return None


def load(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def send_next():
    videos = load(VIDEOS_FILE, [])
    pending = [(i, v) for i, v in enumerate(videos) if not v["done"]][:2]
    if not pending:
        call("sendMessage", chat_id=CHAT_ID, text="خلصت كل الفيديوهات 🎉")
        return
    for i, v in pending:
        text = (
            f"📚 مراجعة النهاردة ({i + 1}/{len(videos)}):\n"
            f"{v['title']}\n{v['url']}\n\n"
            "حل الأسئلة الأول من غير ما تبص على الحل."
        )
        button = {"inline_keyboard": [[{"text": "تم ✅", "callback_data": f"done:{i}"}]]}
        call("sendMessage", chat_id=CHAT_ID, text=text, reply_markup=button)


def handle_updates(state):
    updates = call(
        "getUpdates",
        offset=state["offset"],
        timeout=0,
        allowed_updates=["message", "callback_query"],
    )
    for u in updates:
        state["offset"] = u["update_id"] + 1
        if "message" in u:
            msg = u["message"]
            if msg["chat"]["id"] != CHAT_ID:
                continue
            text = msg.get("text", "")
            if text.startswith("/start"):
                call(
                    "sendMessage",
                    chat_id=CHAT_ID,
                    text="تمام ✅ هبعتلك فيديوهين المراجعة كل يوم الساعة 9 الصبح.\n"
                    "اكتب /today لو عايز فيديوهات دلوقتي.",
                )
            elif text.startswith("/today"):
                send_next()
        elif "callback_query" in u:
            q = u["callback_query"]
            if q["from"]["id"] != CHAT_ID:
                continue
            i = int(q["data"].split(":")[1])
            videos = load(VIDEOS_FILE, [])
            if 0 <= i < len(videos):
                videos[i]["done"] = True
                save(VIDEOS_FILE, videos)
                safe_call(
                    "editMessageText",
                    chat_id=CHAT_ID,
                    message_id=q["message"]["message_id"],
                    text=f"✅ خلصت: {videos[i]['title']}",
                )
            safe_call("answerCallbackQuery", callback_query_id=q["id"])


def daily(state):
    now = datetime.now(CAIRO)
    today = now.date().isoformat()
    if now.hour >= 9 and state.get("last_sent") != today:
        send_next()
        state["last_sent"] = today


def main():
    state = load(STATE_FILE, {"offset": 0, "last_sent": ""})
    handle_updates(state)
    daily(state)
    save(STATE_FILE, state)


if __name__ == "__main__":
    main()