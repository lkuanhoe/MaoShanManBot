import os
import json
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from zoneinfo import ZoneInfo

now_sg = datetime.now(ZoneInfo("Asia/Singapore"))
timestamp = now_sg.strftime("%Y-%m-%d %H:%M:%S")

# Enable logging
logging.basicConfig(level=logging.INFO)

# Define conversation states
NAME, PHONE, DURIAN, QTY, PACKING, ADDRESS, DELIVERYDATE, DELIVERYTIME = range(8)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds_json = os.getenv("GOOGLE_CREDS_JSON")
if not creds_json:
    raise Exception("Missing GOOGLE_CREDS_JSON environment variable")

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Durian Orders").sheet1

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\U0001F349 Welcome to MaoShanMan! What's your name?")
    return NAME

# Handlers for each state
async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("\U0001F4DE Please enter your phone number:")
    return PHONE

async def get_phone(update, context):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("\U0001F348 What durian type? E.g. MSW and Black Thorn. Please refer to our Telegram Channel for more info!")
    return DURIAN

async def get_durian(update, context):
    context.user_data['durian'] = update.message.text
    await update.message.reply_text("\u2696\ufe0f How many kg? E.g. 2kg MSW and 2kg Black Thorn)")
    return QTY

async def get_qty(update, context):
    context.user_data['qty'] = update.message.text
    await update.message.reply_text("Do you want your durians dehusked and packed into plastic containers? Yes/ No")
    return PACKING

async def get_packing(update, context):
    context.user_data['packing'] = update.message.text
    await update.message.reply_text("\U0001F3E0 Enter delivery address in the following format: Block, Street, #Unit number, Singapore XXXXXX")
    return ADDRESS

async def get_address(update, context):
    user_input = update.message.text.strip()
    
    if len(user_input) < 10:
        await update.message.reply_text("That doesn't look like a valid address. Please enter in the format: Block, Street, #Unit number, Singapore XXXXXX")
        return ADDRESS
    
    context.user_data['address'] = user_input
    
    await update.message.reply_text("Thanks for the address! \U0001F4C5 What's your preferred delivery date? E.g. 25 Jun 25")
    return DELIVERYDATE

async def get_deliverydate(update, context):
    context.user_data['deliverydate'] = update.message.text
    await update.message.reply_text("\U0001F552 Please enter your preferred delivery slot (e.g., 9am-12noon/ 2pm-6pm/ 8pm onwards).")
    return DELIVERYTIME

async def get_deliverytime(update, context):
    context.user_data['deliverytime'] = update.message.text

    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_sg = datetime.now(ZoneInfo("Asia/Singapore"))
    timestamp = now_sg.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Order timestamp: {timestamp}")  # <-- Add it here to debug the timestamp

    fields = ['name', 'phone', 'durian', 'qty', 'packing', 'address', 'deliverydate', 'deliverytime']
    row = [context.user_data.get(field, "") for field in fields]
    row_with_timestamp = [timestamp] + row

    try:
        sheet.append_row(row_with_timestamp)
    except Exception as e:
        print("Error writing to sheet:", e)
        await update.message.reply_text("⚠️ Something went wrong while saving your order.")

    await update.message.reply_text("\u2705 Order received! We'll contact you shortly. Thank you!")
    return ConversationHandler.END

# Cancel command
async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("\u274C Order cancelled. You can /start again anytime.")
    return ConversationHandler.END

# Admin command to view last 5 orders
async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = sheet.get_all_values()
    last_orders = orders[-5:] if len(orders) > 5 else orders[1:]
    message = "\U0001F4CB Last 5 Orders:\n"
    for row in last_orders:
        message += f"- {row[1]} ({row[2]}): {row[3]} {row[4]}kg to {row[5]}\n"
    await update.message.reply_text(message)

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DURIAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_durian)],
            QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qty)],
            PACKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_packing)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            DELIVERYDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deliverydate)],
            DELIVERYTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deliverytime)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("vieworders", view_orders))

    app.run_polling()
