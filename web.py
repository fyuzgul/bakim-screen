import imaplib
import email
import threading
from email.header import decode_header
from datetime import datetime
import time
import pytz
import webbrowser
from flask import Flask, render_template, jsonify

app = Flask(__name__)

username = "mekanikbakimcmkkablo@gmail.com"
password = "sbiktfagyinhzjgu"
mail_server = "imap.gmail.com"

emails_info = []
waiting_emails = {}
arrived_emails = {}
processed_emails = set()

def check_emails():
    while True:
        try:
            mail = imaplib.IMAP4_SSL(mail_server)
            mail.login(username, password)
            mail.select("inbox")

            today = datetime.today().strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(ON "{today}" BODY "Makine Mekanik Ariza")')

            if status == "OK":
                email_ids = messages[0].split()
                for email_id in email_ids:
                    if email_id not in processed_emails:
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        msg = email.message_from_bytes(msg_data[0][1])
                        body = get_email_body(msg)
                        email_time = get_email_time(msg)

                        processed_emails.add(email_id)

                        email_info = extract_email_info(body)
                        if email_info:
                            process_email(email_info, email_time)

        except Exception as e:
            print(f"Hata oluÅŸtu: {e}")
        time.sleep(10)

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                return part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        if msg.get_content_type() == "text/plain":
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    return ""

def get_email_time(msg):
    email_time = msg['Date']
    if email_time:
        try:
            # E-posta zamanÄ±nÄ± al ve doÄŸru formata Ã§evir
            parsed_time = email.utils.parsedate_to_datetime(email_time)
            if parsed_time is None:
                raise ValueError("E-posta zamanÄ±nÄ± Ã§Ã¶zemedi.")
            
            # EÄŸer parsed_time'de timezone bilgisi yoksa UTC olarak kabul et
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=pytz.utc)
            
            # Ä°stanbul saatine Ã§evir
            local_tz = pytz.timezone("Europe/Istanbul")
            local_time = parsed_time.astimezone(local_tz)
            return local_time.strftime('%H:%M')
        
        except Exception as e:
            print(f"Tarih formatÄ±nda hata: {e}")
            return "Bilinmiyor"
    return "Bilinmiyor"


def extract_email_info(body):
    info = {}
    lines = body.splitlines()
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip().strip('[]')
    return info

def process_email(email_info, email_time):
    ist_no = email_info.get("IST NO", "")
    ist_durus = email_info.get("IST DURUS ADI", "")

    if "1250'lik Sehpa Arizasi" in ist_durus or "Bekleniyor" in ist_durus or "630'luk Sehpa Arizasi" in ist_durus:
        if ist_no in arrived_emails:
            arrived_emails.pop(ist_no)
        if ist_no not in waiting_emails:
            display_email(email_info, email_time, "waiting")

    elif "Geldi" in ist_durus:
        if ist_no in waiting_emails:
            waiting_emails.pop(ist_no)
            display_email(email_info, email_time, "arrived")
            threading.Thread(target=remove_email_after_delay, args=(ist_no, 180)).start()

def remove_email_after_delay(ist_no, delay):
    time.sleep(delay)
    if ist_no in arrived_emails:
        arrived_emails.pop(ist_no)

def display_email(email_info, email_time, status):
    email_info["Zaman"] = email_time
    ist_no = email_info.get("IST NO", "")
    
    if status == "waiting":
        waiting_emails[ist_no] = email_info

    elif status == "arrived":
        arrived_emails[ist_no] = email_info

@app.route('/')
def index():
    return render_template('index.html', emails=emails_info)

@app.route('/update')
def update_emails():
    global emails_info
    emails_info = list(waiting_emails.values()) + list(arrived_emails.values())
    return jsonify(emails=emails_info)


if __name__ == "__main__":
    threading.Thread(target=check_emails, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)


