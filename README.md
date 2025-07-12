
# 🤖 Clara - Instagram DM Bot (GPT-4o + PostgreSQL)

Un chatbot AI Instagram (Clara) capable de répondre automatiquement aux messages privés Instagram en utilisant **GPT-4o** et une mémoire longue durée avec PostgreSQL.

## 🚀 Fonctionnalités

- Réponses intelligentes via **OpenAI GPT-4o**
- Mémoire de conversation par utilisateur (stockée en PostgreSQL)
- Webhook pour DM Instagram via Meta Graph API

## 📁 Structure du projet

```
.
├── app_ig.py             # Code principal du bot Flask
├── requirements.txt      # Dépendances Python
├── init.sql              # Script d'initialisation PostgreSQL
├── .env.example          # Exemple de fichier d'environnement
```

## 🧪 Configuration locale (optionnelle)

Crée un fichier `.env` avec les valeurs suivantes :

```bash
cp .env.example .env
```

## 🧠 Exemple de réponse

Clara répond de manière fluide, élégante et joueuse. Elle ne révèle jamais qu’elle est une IA.

## 🛠️ Déploiement Render

1. Crée un nouveau service web sur [Render](https://render.com/)
2. Uploade ce dossier ou connecte un repo GitHub
3. Ajoute les variables d’environnement dans l’onglet **Environment** :
   - `VERIFY_TOKEN`
   - `PAGE_ACCESS_TOKEN`
   - `OPENAI_API_KEY`
   - `DATABASE_URL`

4. Crée une base PostgreSQL sur Render (copie `External Database URL`)
5. Exécute le script `init.sql` une fois pour créer la table

## 🧷 Webhook Meta

1. Va sur [developers.facebook.com](https://developers.facebook.com)
2. Crée une app > Lien vers ta page IG business
3. Active **Webhooks** pour le produit Instagram
4. Abonne-toi à l’événement `instagram_messages` avec ton URL Render `/webhook`

## 👩 Exemple de .env

Voir `.env.example`

