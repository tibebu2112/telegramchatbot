# =============================================================================
# PASTE THIS WHOLE FILE INTO ONE GOOGLE COLAB CELL (after the install cell).
# Keep the cell RUNNING so the Telegram bot stays online.
# =============================================================================
# Cell 1 (install) — run once:
#   !pip install -q pyTelegramBotAPI gspread google-auth
# =============================================================================

import json
import os
from datetime import datetime

import gspread
import telebot
from google.oauth2.service_account import Credentials
from telebot import types

# ---------- FILL THESE THREE LINES ----------
BOT_TOKEN = "PASTE_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER"
SHEET_ID = "PASTE_GOOGLE_SHEET_ID"
# Upload your Google service-account JSON in Colab, then put the filename here:
SERVICE_ACCOUNT_FILE = "service_account.json"
# --------------------------------------------

CAMPUSES = [
    "Peda",
    "Poly / BiT",
    "Zenzelma",
    "Sebatamit",
    "Tibebe Ghion",
    "Fashion Technology (Selam)",
    "Yibab",
]

CATEGORIES = [
    "Cafeteria",
    "Dorm",
    "Academic & Technology",
    "Peace & Security",
    "Other",
]

SHEET_NAME = "Complaints"
HEADERS = [
    "Ticket ID",
    "Timestamp",
    "Campus",
    "Category",
    "Description",
    "Location",
    "Photo URL",
    "Anonymous",
    "Name",
    "Phone",
    "Department",
    "Status",
    "Priority",
    "Telegram User ID",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def open_sheet():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        ws = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=2000, cols=20)
        ws.append_row(HEADERS)
    if ws.row_values(1) != HEADERS:
        if not ws.row_values(1):
            ws.append_row(HEADERS)
    return ws


def next_ticket_id(ws) -> str:
    year = datetime.now().year
    values = ws.col_values(1)
    n = max(len(values) - 1, 0) + 1
    return f"#BDU-{year}-{n:03d}"


def keyboard(options, row_width=1):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    for opt in options:
        markup.add(types.KeyboardButton(opt))
    return markup


bot = telebot.TeleBot(BOT_TOKEN)
user_state = {}


@bot.message_handler(commands=["start", "help"])
def start(message):
    user_state[message.chat.id] = {}
    bot.send_message(
        message.chat.id,
        "Welcome to the BDU Student Union complaint bot.\n"
        "Your report helps union leaders fix campus problems with real data.\n\n"
        "Step 1/4 — Choose your campus:",
        reply_markup=keyboard(CAMPUSES),
    )


@bot.message_handler(func=lambda m: True, content_types=["text", "photo"])
def conversation(message):
    chat_id = message.chat.id
    state = user_state.setdefault(chat_id, {})
    text = (message.text or "").strip()

    if "campus" not in state:
        if text not in CAMPUSES:
            bot.send_message(chat_id, "Please choose a campus from the buttons.", reply_markup=keyboard(CAMPUSES))
            return
        state["campus"] = text
        bot.send_message(
            chat_id,
            "Step 2/4 — What kind of problem is this?",
            reply_markup=keyboard(CATEGORIES),
        )
        return

    if "category" not in state:
        if text not in CATEGORIES:
            bot.send_message(chat_id, "Please choose a category from the buttons.", reply_markup=keyboard(CATEGORIES))
            return
        state["category"] = text
        bot.send_message(
            chat_id,
            "Step 3/4 — Describe the problem in a short message.\n"
            "You can also send a photo with a caption.\n"
            "Optional: include building or dorm number.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

    if "description" not in state:
        if message.content_type == "photo":
            state["description"] = message.caption or "(photo attached)"
            state["photo"] = "yes"
        else:
            if len(text) < 5:
                bot.send_message(chat_id, "Please write a bit more detail (at least a few words).")
                return
            state["description"] = text
            state["photo"] = "no"
        bot.send_message(
            chat_id,
            "Optional: send the building / dorm / room (or type Skip).",
            reply_markup=keyboard(["Skip"]),
        )
        state["await_location"] = True
        return

    if state.get("await_location"):
        state["location"] = "" if text.lower() == "skip" else text
        state["await_location"] = False
        bot.send_message(
            chat_id,
            "Step 4/4 — How should we record your identity?",
            reply_markup=keyboard(["Submit anonymously", "Include my name"]),
        )
        return

    if "anonymous" not in state:
        if text == "Submit anonymously":
            state["anonymous"] = "Yes"
            save_and_confirm(chat_id, message.from_user.id, state)
            return
        if text == "Include my name":
            state["anonymous"] = "No"
            bot.send_message(
                chat_id,
                "Send: Name | Phone | Department\nExample: Abebe | 09xxxxxxxx | Civil Engineering",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            return
        bot.send_message(
            chat_id,
            "Please tap one option.",
            reply_markup=keyboard(["Submit anonymously", "Include my name"]),
        )
        return

    if state.get("anonymous") == "No" and "name" not in state:
        parts = [p.strip() for p in text.replace(",", "|").split("|")]
        state["name"] = parts[0] if parts else text
        state["phone"] = parts[1] if len(parts) > 1 else ""
        state["department"] = parts[2] if len(parts) > 2 else ""
        save_and_confirm(chat_id, message.from_user.id, state)
        return


def save_and_confirm(chat_id, user_id, state):
    ws = open_sheet()
    ticket = next_ticket_id(ws)
    priority = "High" if state.get("category") in ("Peace & Security", "Academic & Technology") else "Medium"
    ws.append_row(
        [
            ticket,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state.get("campus", ""),
            state.get("category", ""),
            state.get("description", ""),
            state.get("location", ""),
            state.get("photo", "no"),
            state.get("anonymous", "Yes"),
            state.get("name", ""),
            state.get("phone", ""),
            state.get("department", ""),
            "Open",
            priority,
            str(user_id),
        ]
    )
    bot.send_message(
        chat_id,
        f"Your complaint was registered as {ticket}.\n"
        "The Student Union will follow up.\n\n"
        "Send /start to submit another report.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    user_state.pop(chat_id, None)


if BOT_TOKEN.startswith("PASTE"):
    raise SystemExit("Fill BOT_TOKEN, SHEET_ID, and upload service_account.json first.")

print("Bot is running. Open Telegram, find your bot, send /start. Keep this cell running.")
bot.infinity_polling(skip_pending=True)
