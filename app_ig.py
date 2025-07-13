import os
import time
import random
import json
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv
import openai
import psycopg
from psycopg.rows import dict_row

# Chargement des variables d'environnement
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")

if not all([VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, DATABASE_URL]):
    raise ValueError("❌ Une ou plusieurs variables d'environnement sont manquantes.")

# Connexion à la base de données
conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

# Initialisation du client OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Création de l'application Flask
app = Flask(__name__)

# Route d'accueil
@app.route('/')
def home():
    return "<h1>Clara bot est en ligne 💬</h1><p><a href='/privacy'>Politique de confidentialité</a> | <a href='/terms'>Conditions d'utilisation</a></p>"

# Politique de confidentialité
@app.route('/privacy')
def show_privacy():
    return render_template('privacy.html')

# Conditions d'utilisation
@app.route('/terms')
def show_terms():
    return render_template('condition.html')

# Route de santé pour Render
@app.route('/healthz')
def healthz():
    return "ok", 200

# Vérification du webhook
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Erreur de vérification", 403

# Réception des messages Instagram (DM)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        return "No data", 400

    if 'entry' in data:
        for entry in data['entry']:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                if value.get("messaging_product") == "instagram":
                    messages = value.get("messages", [])
                    for msg in messages:
                        sender_id = msg.get("from")
                        text = msg.get("text", {}).get("body")
                        if sender_id and text:
                            handle_message(sender_id, text)
    return "ok", 200

# Traitement du message utilisateur avec GPT
def handle_message(sender_id, msg):
    u = get_user(sender_id) or {"profile": {}, "history": [], "sent_link": False}
    u["history"] = u.get("history", [])
    u["profile"] = u.get("profile", {})
    u["sent_link"] = u.get("sent_link", False)

    u["history"].append({"role": "user", "content": msg})
    if len(u["history"]) > 10:
        u["history"] = u["history"][-10:]

    sys_prompt = "Tu es Clara, une femme spontanée, joueuse, élégante. Tu ne dis jamais que tu es une IA."
    messages = [{"role": "system", "content": sys_prompt}] + u["history"]

    try:
        rsp = client.chat.completions.create(model="gpt-4o", messages=messages)
        reply = rsp.choices[0].message.content.strip()
        u["history"].append({"role": "assistant", "content": reply})
        send_message_ig(sender_id, reply)
    except Exception as e:
        print("Erreur GPT :", e)
        send_message_ig(sender_id, "Oups, petit bug ! Tu peux me répéter ?")
    save_user(sender_id, u)

# Fonction pour envoyer un message à Instagram
def send_message_ig(user_id, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "messaging_product": "instagram",
        "recipient": {"id": user_id},
        "message": {"text": text}
    }
    response = requests.post(url, headers=headers, params={"access_token": PAGE_ACCESS_TOKEN}, json=payload)
    if response.status_code != 200:
        print("Erreur envoi IG :", response.text)

# Récupérer les données utilisateur
def get_user(uid):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_memory WHERE user_id = %s", (uid,))
        return cur.fetchone()

# Sauvegarder l'état utilisateur
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

# Route pour le callback OAuth Instagram
@app.route('/auth/instagram/callback')
def instagram_callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return f"❌ Erreur lors de l'autorisation : {error}", 400
    if not code:
        return "❌ Code d'autorisation manquant.", 400

    print("✅ Code reçu :", code)
    return "✅ Autorisation réussie ! Vous pouvez fermer cette fenêtre.", 200

# Route de test manuelle pour envoyer un message test à ton compte Instagram
@app.route('/test-send')
def test_send():
    user_id = "17841470881545429"  # Ton Instagram User ID
    test_message = "Ceci est un test automatisé de Clara 🤖"
    send_message_ig(user_id, test_message)
    return "✅ Message de test envoyé à Clara !", 200
# Lancement de l'application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
