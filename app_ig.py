import os
import time
import random
import json
import requests
from threading import Thread
from datetime import datetime
from flask import Flask, request, send_from_directory
from dotenv import load_dotenv
import openai
import psycopg
from psycopg.rows import dict_row

load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not all([VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, DATABASE_URL]):
    raise ValueError("❌ VERIFY_TOKEN / PAGE_ACCESS_TOKEN / OPENAI_API_KEY / DATABASE_URL manquant.")

conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
client = openai.OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)
CLARA_PICS = [
    "https://raw.githubusercontent.com/visibilitecom/bot-messenger-gpt/main/images/clara1.png",
    "https://raw.githubusercontent.com/visibilitecom/bot-messenger-gpt/main/images/clara2.png",
    "https://raw.githubusercontent.com/visibilitecom/bot-messenger-gpt/main/images/clara3.png",
]

def get_user(uid):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_memory WHERE user_id = %s", (uid,))
        return cur.fetchone()

def save_user(uid, data):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_memory (user_id, profile, history, last_seen, sent_link)
            VALUES (%s, %s, %s, NOW(), %s)
            ON CONFLICT (user_id)
            DO UPDATE SET profile = EXCLUDED.profile,
                          history = EXCLUDED.history,
                          last_seen = EXCLUDED.last_seen,
                          sent_link = EXCLUDED.sent_link
            """,
            (uid, json.dumps(data["profile"]), json.dumps(data["history"]), data["sent_link"])
        )
        conn.commit()

def send_typing(sid):
    requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        headers={"Content-Type": "application/json"},
        json={"recipient": {"id": sid}, "sender_action": "typing_on"},
    )

def send_message(rid, text):
    requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        headers={"Content-Type": "application/json"},
        json={"recipient": {"id": rid}, "message": {"text": text}},
    )

def send_image(rid, url):
    requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        headers={"Content-Type": "application/json"},
        json={
            "recipient": {"id": rid},
            "message": {"attachment": {"type": "image", "payload": {"url": url, "is_reusable": True}}}
        },
    )

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Erreur de vérification", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'entry' in data:
        for entry in data['entry']:
            for event in entry.get('messaging', []):
                sid = event['sender']['id']
                if 'message' in event and 'text' in event['message']:
                    handle_message(sid, event['message']['text'])
    return "ok", 200

def handle_message(sender_id, msg):
    u = get_user(sender_id) or {"profile": {}, "history": [], "sent_link": False}
    u["history"] = u.get("history", [])
    u["profile"] = u.get("profile", {})
    u["sent_link"] = u.get("sent_link", False)

    u["history"].append({"role": "user", "content": msg})
    if len(u["history"]) > 10:
        u["history"] = u["history"][-10:]

    send_typing(sender_id)
    time.sleep(random.uniform(1.5, 3.0))

    sys_prompt = "Tu es Clara, une femme spontanée, joueuse, élégante. Tu ne dis jamais que tu es une IA."
    msgs = [{"role": "system", "content": sys_prompt}] + u["history"]

    try:
        rsp = client.chat.completions.create(model="gpt-4o", messages=msgs)
        reply = rsp.choices[0].message.content.strip()
        u["history"].append({"role": "assistant", "content": reply})
        send_message(sender_id, reply)
    except:
        send_message(sender_id, "Oups, bug ! Répète voir ?")

    save_user(sender_id, u)

@app.route('/privacy')
def privacy():
    return send_from_directory('.', 'privacy.html')

@app.route('/healthz')
def healthz():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
