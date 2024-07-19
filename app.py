from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import os
import pytz

app = Flask(__name__)

# Environment variables for LINE API
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
    url = Column(String, unique=True)
    is_alive = Column(Boolean, default=True)
    checked_at = Column(DateTime)

Base.metadata.create_all(engine)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    if text.startswith("https://") or text.startswith("http://"):
        response = save_link(user_id, text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
    elif text.lower() == "my links":
        links = get_links(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=links))

def save_link(user_id, url):
    existing_link = session.query(Link).filter_by(user_id=user_id, url=url).first()
    if existing_link is None:
        new_link = Link(user_id=user_id, url=url, checked_at=datetime.now())
        session.add(new_link)
        session.commit()
        return f"Link saved: {url}"
    else:
        return f"Link already exists: {url}"

def get_links(user_id):
    links = session.query(Link).filter_by(user_id=user_id).all()
    if links:
        response = "\n".join([f"{link.url} - {'Alive' if link.is_alive else 'Dead'}" for link in links])
    else:
        response = "No links found."
    return response

def is_link_alive(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def check_links():
    links = session.query(Link).all()
    for link in links:
        link.is_alive = is_link_alive(link.url)
        link.checked_at = datetime.now()
    session.commit()

# Use pytz for the timezone
timezone = pytz.utc

scheduler = BackgroundScheduler(timezone=timezone)
scheduler.add_job(check_links, 'interval', hours=1)
scheduler.start()

if __name__ == "__main__":
    app.run()
