import os
import json
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv
import openai
import psycopg
from psycopg.rows import dict_row
from datetime import datetime

# Chargement des variables d'environnement
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not all([VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, DATABASE_URL]):
    raise ValueError("❌ Une ou plusieurs variables d'environnement sont manquantes.")

# Connexion à PostgreSQL
conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

# OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# App Flask
app = Flask(__name__)

# Mémoire temporaire pour afficher le dernier user Instagram ayant écrit
latest_user = {"id": None, "time": None}

@app.route('/')
def home():
    return "<h1>🤖 Clara bot est en ligne</h1><p><a href='/privacy'>Politique</a> | <a href='/terms'>Conditions</a></p>"

@app.route('/privacy')
def show_privacy():
    return render_template('privacy.html')

@app.route('/terms')
def show_terms():
    return render_template('condition.html')

@app.route('/healthz')
def healthz():
    return "ok", 200

@app.route('/last-user-id')
def last_user_id():
    if latest_user["id"]:
        return f"🆔 Dernier sender_id : {latest_user['id']} (à {latest_user['time']})", 200
    return "❌ Aucun message Instagram reçu pour l’instant.", 200

# ✅ Création manuelle de la table user_memory
@app.route('/init-db')
def init_db_route():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT PRIMARY KEY,
                    profile JSONB,
                    history JSONB,
                    last_seen TIMESTAMP,
                    sent_link BOOLEAN DEFAULT FALSE
                );
            """)
            conn.commit()
        return "✅ Table user_memory créée avec succès", 200
    except Exception as e:
        print("❌ Erreur création de la table :", e)
        return f"Erreur : {e}", 500

# Vérification du webhook Meta
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook vérifié")
        return challenge, 200
    return "❌ Échec de la vérification", 403

# Réception des DM Instagram
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📩 Données reçues :\n", json.dumps(data, indent=2))

    if 'entry' in data:
        for entry in data['entry']:
            messaging_events = entry.get("messaging", [])
            for event in messaging_events:
                sender_id = event.get("sender", {}).get("id")
                text = event.get("message", {}).get("text")

                print("👤 Sender ID :", sender_id)
                print("💬 Message :", text)

                if sender_id and text:
                    latest_user["id"] = sender_id
                    latest_user["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    handle_message(sender_id, text)

    return "ok", 200

# Traitement du message avec GPT
def handle_message(sender_id, msg):
    user_data = get_user(sender_id) or {"profile": {}, "history": [], "sent_link": False}
    user_data["history"].append({"role": "user", "content": msg})
    user_data["history"] = user_data["history"][-10:]

    messages = [
        {"role": "system", "content": "Tu es Clara, une femme élégante, joueuse, naturelle. Tu ne dis jamais que tu es une IA."},
        *user_data["history"]
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        reply = response.choices[0].message.content.strip()
        print("🤖 Réponse GPT :", reply)

        user_data["history"].append({"role": "assistant", "content": reply})
        send_message_ig(sender_id, reply)
    except Exception as e:
        print("❌ Erreur OpenAI :", e)
        send_message_ig(sender_id, "Oups, petit bug… Tu peux me redire ?")

    save_user(sender_id, user_data)

# Envoi du message avec logs détaillés
def send_message_ig(user_id, text):
    try:
        url = "https://graph.facebook.com/v23.0/me/messages"
        headers = {"Content-Type": "application/json"}
        payload = {
            "messaging_product": "instagram",
            "recipient": {"id": user_id},
            "message": {"text": text}
        }

        print("📤 Préparation de l'envoi IG vers :", user_id)
        print("📤 Message :", text)

        response = requests.post(url, headers=headers, params={"access_token": PAGE_ACCESS_TOKEN}, json=payload)

        print("📤 Envoi IG status:", response.status_code)
        print("📤 Réponse IG:", response.text)

        if response.status_code != 200:
            print("⚠️ Envoi échoué. Vérifie le token ou l'ID utilisateur.")
    except Exception as e:
        print("❌ Exception lors de l’envoi IG :", e)

# Lecture de la mémoire utilisateur
def get_user(uid):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_memory WHERE user_id = %s", (uid,))
        return cur.fetchone()

# Sauvegarde mémoire utilisateur
def save_user(uid, data):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO user_memory (user_id, profile, history, last_seen, sent_link)
            VALUES (%s, %s, %s, NOW(), %s)
            ON CONFLICT (user_id)
            DO UPDATE SET profile = EXCLUDED.profile,
                          history = EXCLUDED.history,
                          last_seen = EXCLUDED.last_seen,
                          sent_link = EXCLUDED.sent_link
        """, (
            uid,
            json.dumps(data["profile"]),
            json.dumps(data["history"]),
            data["sent_link"]
        ))
        conn.commit()

# Test manuel d'envoi
@app.route('/test-last-user')
def test_send_to_last_user():
    if latest_user["id"]:
        test_message = f"🧪 Clara est bien en ligne (test à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        send_message_ig(latest_user["id"], test_message)
        return f"✅ Message test envoyé à {latest_user['id']}", 200
    return "❌ Aucun utilisateur Instagram connu pour l'instant.", 200

if __name__ == "__main__":
    import logging
    import sys

    # Activation des logs détaillés + affichage immédiat sur Render
    logging.basicConfig(level=logging.DEBUG)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    port = int(os.environ.get("PORT", 5000))
    is_render = os.environ.get("RENDER", "0") == "1"

    print("🚀 Démarrage de Clara bot sur le port", port)

    if is_render:
        print("📡 Environnement Render détecté — pas d'envoi automatique (attente d’un vrai message Instagram)")
    else:
        print("💻 Environnement local détecté — démarrage sans envoi")

    app.run(host="0.0.0.0", port=port)

