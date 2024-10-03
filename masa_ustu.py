import imaplib
import email
from email.header import decode_header
from datetime import datetime
import time
import threading
import tkinter as tk
import pytz

username = "muhammedfthyzgl@gmail.com"
password = "fplflbpsyemswkoo"
mail_server = "imap.gmail.com"

class EmailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("E-posta Gövdesi İzleyici")
        self.root.attributes('-fullscreen', True)  
        self.processed_emails = set()
        self.blinking_rows = []  
        self.waiting_emails = {}  # Bekleniyor durumundaki IST NO'lar için liste
        self.arrived_emails = {}  # Geldi durumundaki IST NO'lar için liste
        self.row_count = 0  # Satır sayısını manuel olarak takip edeceğiz

        self.create_headers()
        threading.Thread(target=self.check_emails, daemon=True).start()

    def create_headers(self):
        header_frame = tk.Frame(self.root, bd=2, relief=tk.SOLID)
        header_frame.pack(fill=tk.X)

        # Başlıklar
        headers = ["IST NO", "IST ADI", "IST DURUS ADI", "Bildirim Zamanı"]
        header_widths = [3, 3, 2, 1]  
        for index, header in enumerate(headers):
            header_label = tk.Label(header_frame, text=header, font=("Arial", 20, "bold"), padx=5, pady=5)
            header_label.grid(row=0, column=index, padx=10, pady=5, sticky="ew")
            header_frame.grid_columnconfigure(index, weight=header_widths[index])  # Başlık genişliği ayarı

        # Veri çerçevesi
        self.data_frame = tk.Frame(self.root)
        self.data_frame.pack(fill=tk.BOTH, expand=True)

    def check_emails(self):
        while True:
            try:
                mail = imaplib.IMAP4_SSL(mail_server)
                mail.login(username, password)
                mail.select("inbox")

                today = datetime.today().strftime("%d-%b-%Y")
                status, messages = mail.search(None, f'(ON "{today}" BODY "Bakim Personeli")')

                if status == "OK":
                    email_ids = messages[0].split()
                    for email_id in email_ids:
                        if email_id not in self.processed_emails:
                            status, msg_data = mail.fetch(email_id, '(RFC822)')
                            msg = email.message_from_bytes(msg_data[0][1])
                            body = self.get_email_body(msg)
                            email_time = self.get_email_time(msg)

                            self.processed_emails.add(email_id)

                            email_info = self.extract_email_info(body)
                            if email_info:
                                self.process_email(email_info, email_time)

            except Exception as e:
                print(f"Hata oluştu: {e}")
            time.sleep(10)

    def get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            if msg.get_content_type() == "text/plain":
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""

    def get_email_time(self, msg):
        email_time = msg['Date']
        if email_time:
            parsed_time = email.utils.parsedate_to_datetime(email_time)
            local_tz = pytz.timezone("Europe/Istanbul")
            local_time = parsed_time.replace(tzinfo=pytz.utc).astimezone(local_tz)
            return local_time.strftime('%H:%M')
        return "Bilinmiyor"

    def extract_email_info(self, body):
        info = {}
        lines = body.splitlines()
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip().strip('[]')
        return info

    def process_email(self, email_info, email_time):
        ist_no = email_info.get("IST NO", "")
        ist_durus = email_info.get("IST DURUS ADI", "")

        if "Bekleniyor" in ist_durus:
            if ist_no in self.arrived_emails:
                # Eğer geldi durumu varsa önce onu kaldır
                self.clear_row(self.arrived_emails.pop(ist_no))
            if ist_no not in self.waiting_emails:
                self.display_email(email_info, email_time, "waiting")

        elif "Geldi" in ist_durus:
            if ist_no in self.waiting_emails:
                # Eğer bekleniyor durumu varsa önce onu kaldır
                self.clear_row(self.waiting_emails.pop(ist_no))
                self.display_email(email_info, email_time, "arrived")

    def display_email(self, email_info, email_time, status):
        # Mevcut satır sayısını row_count ile takip edin
        row = self.row_count
        self.row_count += 1  # Yeni e-posta eklendiğinde satır sayısını artırın
        
        email_values = [
            email_info.get("IST NO", ""),
            email_info.get("IST ADI", ""),
            email_info.get("IST DURUS ADI", ""),
            email_time
        ]

        row_labels = []
        for index, value in enumerate(email_values):
            email_label = tk.Label(self.data_frame, text=value, font=("Arial", 20), padx=5, pady=5, wraplength=400)
            email_label.grid(row=row, column=index, padx=10, pady=5, sticky="ew")
            row_labels.append(email_label)

        if status == "waiting":
            self.blinking_rows.append(row_labels)  # Yanıp sönme efekti ekle
            self.blink_row(row_labels)
            self.waiting_emails[email_values[0]] = row_labels  # Bekleniyor durumunu sakla

        elif status == "arrived":
            for label in row_labels:
                label.config(foreground="green")  # Geldi mesajı için yeşil renkte
            self.arrived_emails[email_values[0]] = row_labels  # Geldi durumunu sakla

        # Her sütunun genişliğini ayarlama
        self.data_frame.grid_columnconfigure(0, weight=3)  # IST NO
        self.data_frame.grid_columnconfigure(1, weight=4)  # IST ADI
        self.data_frame.grid_columnconfigure(2, weight=3)  # IST DURUS ADI (daha geniş)
        self.data_frame.grid_columnconfigure(3, weight=1)  # E-posta Zamanı

    def clear_row(self, row_labels):
        for label in row_labels:
            label.destroy()  # Satırdaki tüm etiketleri sil

    def blink_row(self, labels):
        current_color = labels[0].cget("foreground")
        new_color = "red" if current_color == "black" else "black"
        for label in labels:
            label.config(foreground=new_color) 
        self.root.after(500, lambda: self.blink_row(labels))  


if __name__ == "__main__":
    root = tk.Tk()
    app = EmailApp(root)
    root.mainloop()
