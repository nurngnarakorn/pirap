from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests

app = Flask(__name__)

# Channel secret และ access token ของคุณ
LINE_CHANNEL_ACCESS_TOKEN = 'BqT2qUiV7shCikgDoy+iLzbNt9/d20lVdNGAnC3g+0hOn0ocA8O/WPUvv4MsNFFRjQFqrsllocCC0SGj+37TbvmpxpQJGVGyIxNrQy2ej6QWVezckV9+6tXq/4QjcXmm298xz1iellFbdBvdW2HUbQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'ed710f52069b6235ca3a134d5a59bac4'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    if text.startswith('http'):
        if not is_link_alive(text):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ลิงค์นี้ไม่สามารถเข้าถึงได้: {text}")
            )

if __name__ == "__main__":
    app.run()

