from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
import math
import os

# Define states
AMOUNT, BANK, LOAN_TYPE, INTEREST_RATE, DURATION = range(5)

# Bank Data
BANKS = {
    "State Bank": {"Home Loan": 8.25, "Personal Loan": 11.45, "Car Loan": 9.0},
    "Union Bank": {"Home Loan": 8.1, "Personal Loan": 11.15, "Car Loan": 8.5},
    "Canara Bank": {"Home Loan": 8.25, "Personal Loan": 10.7, "Car Loan": 9.0, "Gold Loan": 9.0, "Education Loan": 9.25},
    "ICIC Bank": {"Home Loan": 8.75, "Personal Loan": 10.85, "Car Loan": 8.5, "Gold Loan": 9.25, "Education Loan": 8.30},
    "Axis Bank": {"Home Loan": 8.75, "Personal Loan": 11.10, "Car Loan": 9.0, "Gold Loan": 17.0, "Education Loan": 9.25},
    "HDFC Bank": {"Home Loan": 8.75, "Personal Loan": 10.85, "Car Loan": 8.5, "Gold Loan": 9.30, "Education Loan": 13.70},
    "Bank of Baroda": {"Home Loan": 8.15, "Personal Loan": 11.05, "Car Loan": 8.5, "Gold Loan": 9.15, "Education Loan": 8.15},
    "Kotak Mahindra Bank": {"Home Loan": 8.15, "Personal Loan": 11.05, "Car Loan": 8.5, "Gold Loan": 9.15, "Education Loan": 8.15}
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ---------------- Handlers ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Enter loan amount:")
    return AMOUNT

async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['amount'] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter valid numeric amount.")
        return AMOUNT

    keyboard = [
        ["State Bank", "Union Bank"],
        ["Canara Bank", "ICIC Bank"],
        ["Axis Bank", "HDFC Bank"],
        ["Bank of Baroda", "Kotak Mahindra Bank"]
    ]

    await update.message.reply_text(
        "Select bank:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return BANK

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bank'] = update.message.text

    keyboard = [["Home Loan", "Personal Loan", "Car Loan"],
                ["Gold Loan", "Education Loan", "Custom"]]

    await update.message.reply_text(
        "Select loan type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return LOAN_TYPE

async def loan_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loan = update.message.text
    bank = context.user_data['bank']

    if loan == "Custom":
        await update.message.reply_text("Enter custom interest rate (% per annum):")
        return INTEREST_RATE

    if loan in BANKS.get(bank, {}):
        context.user_data['interest_rate'] = BANKS[bank][loan]
        await update.message.reply_text("Enter loan duration (in years):")
        return DURATION

    await update.message.reply_text("Invalid option. Select again.")
    return LOAN_TYPE

async def interest_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['interest_rate'] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter valid interest rate.")
        return INTEREST_RATE

    await update.message.reply_text("Enter loan duration (in years):")
    return DURATION

async def duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        years = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter valid number of years.")
        return DURATION

    amount = context.user_data['amount']
    rate = context.user_data['interest_rate'] / 12 / 100
    months = years * 12

    if rate == 0:
        emi = amount / months
    else:
        emi = (amount * rate * math.pow(1 + rate, months)) / (math.pow(1 + rate, months) - 1)

    await update.message.reply_text(f"Monthly EMI: ₹{emi:.2f}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# ---------------- Conversation ---------------- #

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount)],
        BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bank)],
        LOAN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, loan_type)],
        INTEREST_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, interest_rate)],
        DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

telegram_app.add_handler(conv_handler)

# ---------------- Webhook Route ---------------- #

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# ---------------- Startup Event ---------------- #

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.shutdown()