from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Read secrets from environment variables
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///links.db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    url = Column(String)
    is_alive = Column(Boolean, default=True)
    checked_at = Column(DateTime)

Base.metadata.create_all(engine)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def is_link_alive(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id

    if text.startswith('http'):
        # Save link to database
        link = session.query(Link).filter_by(url=text, user_id=user_id).first()
        if not link:
            link = Link(url=text, user_id=user_id)
            session.add(link)
            session.commit()
        # Check link immediately
        if not is_link_alive(text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ลิงค์นี้ไม่สามารถเข้าถึงได้: {text}")
            )
    elif text == "แสดงลิงค์ทั้งหมดของฉัน":
        links = session.query(Link).filter_by(user_id=user_id).all()
        if links:
            messages = [f"URL: {link.url} - สถานะ: {'ใช้งานได้' if link.is_alive else 'ใช้งานไม่ได้'}" for link in links]
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(messages))
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="คุณไม่มีลิงค์ที่บันทึกไว้")
            )

def check_links():
    links = session.query(Link).all()
    for link in links:
        alive = is_link_alive(link.url)
        if link.is_alive != alive:
            link.is_alive = alive
            link.checked_at = datetime.now()
            session.commit()
            if not alive:
                line_bot_api.push_message(
                    link.user_id,
                    TextSendMessage(text=f"ลิงค์นี้ไม่สามารถเข้าถึงได้: {link.url}")
                )

scheduler = BackgroundScheduler()
scheduler.add_job(check_links, 'interval', hours=1)
scheduler.start()

if __name__ == "__main__":
    app.run()
