# 📋 Telegram Survey Bot

A fully-featured survey platform built on Telegram.  
Admins create and manage surveys; anyone can answer them.  
Results are stored in **Google Sheets** and visualised in a **Streamlit dashboard**.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Question types** | Likert (1–5), Multiple Choice, Ranking (tap in order) |
| **Admin panel** | Create / edit / delete surveys and questions via inline buttons |
| **Role control** | Admin IDs hardcoded in `.env` — everyone else is a respondent |
| **Duplicate prevention** | Each user can only submit a survey once |
| **Live dashboard** | Streamlit dashboard with charts for every question type |
| **Google Sheets** | All responses saved to one master sheet |

---

## 🗂 Project Structure

```
survey_bot/
├── backend/
│   ├── bot.py                        ← Main entry point
│   ├── config.py                     ← Loads .env variables
│   ├── database.py                   ← SQLite (surveys, questions, options)
│   ├── handlers/
│   │   ├── admin_handlers.py         ← /admin conversation (CRUD)
│   │   ├── survey_handlers.py        ← /surveys conversation (taking)
│   │   └── common_handlers.py        ← /start, /help
│   ├── services/
│   │   └── sheets_service.py         ← Google Sheets writer
│   └── requirements.txt
├── frontend/
│   ├── app.py                        ← Streamlit dashboard
│   ├── sheets_reader.py              ← Google Sheets reader
│   └── requirements.txt
├── credentials/
│   └── README.md                     ← Instructions for service account key
├── .env.example                      ← Copy to .env and fill in values
├── .gitignore
└── README.md
```

---

## 🚀 Setup

### 1 — Clone / open in VS Code

```bash
git clone <your-repo>
cd survey_bot
```

### 2 — Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789               # Your Telegram user ID(s), comma-separated
GOOGLE_CREDENTIALS_FILE=credentials/service_account.json
GOOGLE_SHEET_NAME=Survey Responses
DATABASE_PATH=survey_bot.db
```

> **Finding your Telegram user ID:** Message [@userinfobot](https://t.me/userinfobot) on Telegram.  
> **Getting a bot token:** Message [@BotFather](https://t.me/BotFather) and use `/newbot`.

### 3 — Set up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable **Google Sheets API** + **Google Drive API**.
3. Create a **Service Account**, generate a JSON key, download it.
4. Rename it `service_account.json` and place it in `credentials/`.
5. Share your Google Sheet with the service account's `client_email`.

See `credentials/README.md` for detailed steps.

### 4 — Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 5 — Run the bot

```bash
cd backend
python bot.py
```

### 6 — Install and run the Streamlit dashboard

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at **http://localhost:8501**.

---

## 🤖 Bot Commands

### For Everyone
| Command | Description |
|---|---|
| `/start` | Welcome message + active survey count |
| `/surveys` | List active surveys and take one |
| `/help` | Show all commands |
| `/cancel` | Cancel the current operation |

### Admin Only
| Command | Description |
|---|---|
| `/admin` | Open the admin panel |

---

## 🔧 Admin Workflow

```
/admin
  ├── 📋 List Surveys
  │     └── [Select survey]
  │           ├── ✏️ Edit Title
  │           ├── 📝 Edit Description
  │           ├── ❓ Manage Questions
  │           │     ├── [Select question]
  │           │     │     ├── ✏️ Edit Question Text
  │           │     │     ├── 📝 Manage Options  (MCQ / Ranking only)
  │           │     │     └── 🗑️ Delete Question
  │           │     └── ➕ Add Question
  │           ├── 🟢/🔴 Toggle Active/Inactive
  │           └── 🗑️ Delete Survey
  └── ➕ Create Survey
        ├── Enter title
        ├── Enter description
        └── Add questions (Likert / MCQ / Ranking)
```

---

## 📊 Survey-Taking Workflow

```
/surveys
  └── [Select survey]
        └── Confirm start
              └── Question 1 ... N
                    ├── Likert   → tap 1–5
                    ├── MCQ      → tap an option
                    └── Ranking  → tap options in preferred order
                          └── ✅ Saved to Google Sheets
```

---

## 📈 Google Sheets Structure

All responses land in the **Responses** tab with these columns:

| Timestamp | Survey ID | Survey Title | User ID | Username | First Name | Question # | Question Text | Question Type | Answer |
|---|---|---|---|---|---|---|---|---|---|

---

## 🛡 Security Notes

- **Admin IDs** are stored in `.env`, not the database — they cannot be changed at runtime.
- The SQLite database only tracks *who has completed* each survey (no answer text stored locally).
- **Never commit** `credentials/service_account.json` or `.env` to version control.
