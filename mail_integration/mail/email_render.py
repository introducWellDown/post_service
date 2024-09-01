import os
import django

# Инициализация Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mail_integration.settings')
django.setup()

import re
import imaplib
import email
from email.header import decode_header
from django.conf import settings
from .models import EmailMessage
from datetime import datetime



def decode_mime_words(s):
    decoded_fragments = decode_header(s)
    return ''.join(
        str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes) else str(t[0])
        for t in decoded_fragments
    )

def decode_text(text_bytes):
    try:
        return text_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return text_bytes.decode('latin-1')
        except UnicodeDecodeError:
            return text_bytes.decode('windows-1252', errors='replace')

def fetch_emails(email_account, password, since_date=None):
    messages = []
    try:
        # Подключаемся к серверу IMAP
        mail = imaplib.IMAP4_SSL('imap.yandex.ru')
        mail.login(email_account, password)
        mail.select("inbox")

        # Получаем все сообщения, которые новее последнего загруженного
        search_criteria = '(SINCE "{}")'.format(since_date.strftime('%d-%b-%Y')) if since_date else 'ALL'
        status, data = mail.search(None, search_criteria)
        if status != 'OK':
            print(f"Error during search: {status}")
            return messages

        for num in data[0].split():
            status, msg_data = mail.fetch(num, "(UID RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Получение UID
                    uid = num.decode()

                    # Декодирование заголовков и текста письма
                    subject = decode_mime_words(msg.get("subject", "No Subject"))

                    # Парсинг даты получения сообщения
                    received_date_str = msg.get("date", "")
                    received_date_str_clean = re.sub(r'\s*\(.*?\)\s*', '', received_date_str)

                    try:
                        parsed_received_date = datetime.strptime(received_date_str_clean, '%a, %d %b %Y %H:%M:%S %z')
                    except ValueError:
                        parsed_received_date = datetime.strptime(received_date_str_clean, '%d %b %Y %H:%M:%S %z')

                    body = ""
                    attachments = []

                    # Обработка вложений и содержания письма
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body += decode_text(part.get_payload(decode=True))
                                except Exception as e:
                                    print(f"Failed to decode body: {e}")
                            elif "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename:
                                    filename = decode_mime_words(filename)
                                    filepath = os.path.join(settings.MEDIA_ROOT, filename)
                                    try:
                                        with open(filepath, "wb") as f:
                                            f.write(part.get_payload(decode=True))
                                        attachments.append(filepath)
                                    except Exception as e:
                                        print(f"Failed to save attachment {filename}: {e}")
                    else:
                        try:
                            body += decode_text(msg.get_payload(decode=True))
                        except Exception as e:
                            print(f"Failed to decode non-multipart body: {e}")

                    messages.append({
                        'id': uid,
                        'uid': uid,  # Используем UID как идентификатор сообщения
                        'subject': subject,
                        'sent_date': msg.get("date", ""),
                        'received_date': msg.get("date", ""),
                        'received_date_obj': parsed_received_date,
                        'body': body,
                        'attachments': attachments  # Список путей к файлам
                    })

        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error fetching emails: {e}")

    return messages