import os
import random
import threading
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from main.config import API_TOKEN
from kill_zombie import kill_zombie_processes

# --- Запуск утилиты ---
kill_zombie_processes()

# --- Константы ---
CARD_FOLDER = "card_images"
WEBAPP_URL = "https://8b42d324-2877-4246-93e5-0f1f6f86f54b-00-3itk9fs93va57.worf.replit.dev/"

RARITY_WEIGHTS = {
    'common': 70,
    'rare': 20,
    'super rare': 7,
    'ultra rare': 2.5,
    'mythic': 0
}

# --- Flask и SQLAlchemy ---
app = Flask(__name__, instance_relative_config=True)
db_path = os.path.join(app.instance_path, 'tgcards.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)

# --- Модели ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    tokens = db.Column(db.Integer, default=5)
    currency = db.Column(db.Integer, default=0)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(255))
    rarity = db.Column(db.String(20))
    image = db.Column(db.String(255))
    reward = db.Column(db.Integer)

class UserCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'))
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'))

# --- Flask Routes ---
@app.route("/")
def index():
    return render_template("main.html")

@app.route("/home")
def home():
    user_id = request.args.get("user_id", "")
    return render_template("main.html", user_id=user_id)

@app.route("/cards/<filename>")
def serve_card(filename):
    return send_from_directory(CARD_FOLDER, filename)

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/shop")
def shop():
    return render_template("shop.html")

@app.errorhandler(404)
def page_not_found(e):
    return "Страница не найдена", 404

# --- API Routes ---
@app.route("/api/register_user", methods=["POST"])
def register_user():
    data = request.get_json()
    user_id = str(data.get("user_id"))

    if not user_id:
        return jsonify({"status": "error", "message": "No user_id provided"}), 400

    existing = User.query.filter_by(user_id=user_id).first()
    if existing:
        return jsonify({"status": "ok", "message": "User already exists"}), 200

    db.session.add(User(user_id=user_id, tokens=5, currency=5))
    db.session.commit()
    return jsonify({"status": "ok", "message": f"User {user_id} added"}), 201

@app.route("/api/open-card")
def open_card():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id обязателен"}), 400

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
    if user.tokens < 1:
        return jsonify({"error": "Недостаточно фишек!"}), 400

    card = choose_card()
    if not card:
        return jsonify({"error": "Нет доступных карт"}), 400

    user.tokens -= 1
    user.currency += card.reward
    db.session.add(UserCard(user_id=user_id, card_id=card.id))
    db.session.commit()

    return jsonify({
        "name": card.name,
        "description": card.description,
        "rarity": card.rarity,
        "image": f"/cards/{card.image}",
        "reward": card.reward,
        "tokens": user.tokens,
        "currency": user.currency
    })

@app.route("/api/user-balance")
def user_balance():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id отсутствует'}), 400

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'tokens': 0, 'currency': 0})
    return jsonify({'tokens': user.tokens, 'currency': user.currency})

# --- Telegram Bot Setup ---
router = Router()
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    now = datetime.now(timezone.utc)
    if message.date < now - timedelta(seconds=10):
        return

    if message.from_user is None:
        logging.warning("Получено сообщение без from_user")
        return

    user_id = str(message.from_user.id)

    with app.app_context():
        if not User.query.filter_by(user_id=user_id).first():
            db.session.add(User(user_id=user_id, tokens=5, currency=5))
            db.session.commit()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть мини-приложение",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?user_id={user_id}")
        )]
    ])

    await message.answer(
        "👋 Добро пожаловать! Нажми кнопку ниже, чтобы открыть мини-приложение.",
        reply_markup=keyboard
    )

# --- Утилита выбора карты ---
def choose_card():
    rarities = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    cards = Card.query.filter_by(rarity=chosen_rarity).all()
    return random.choice(cards) if cards else None

# --- Запуск ---
def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)

def start_bot():
    asyncio.run(dp.start_polling(bot))

def main():
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    main()
