import json
from channels.generic.websocket import WebsocketConsumer
from .email_render import fetch_emails
from .models import EmailMessage, EmailAccount
from datetime import datetime
from time import sleep

class MailConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        email_account_str = data.get('email')
        password = data.get('password')

        # Получаем или создаем аккаунт
        email_account, created = EmailAccount.objects.get_or_create(email=email_account_str)
        if created or not email_account.password:
            email_account.password = password
            email_account.save()

        # Получаем все UID сообщений, которые уже сохранены в базе данных для этого аккаунта
        existing_uids = set(EmailMessage.objects.filter(email_account=email_account).values_list('uid', flat=True))

        # Поиск новых сообщений на почте
        new_messages = fetch_emails(email_account_str, password)

        # Фильтрация новых сообщений, которых еще нет в базе данных
        filtered_messages = [msg for msg in new_messages if msg['uid'] not in existing_uids]

        if not filtered_messages:
            # Отправляем сообщение о том, что новых сообщений нет
            self.send(text_data=json.dumps({
                'type': 'complete',
                'status': 'Новых сообщений нет.'
            }))
            return
        
        total_new_messages = len(filtered_messages)
        messages_added = 0

        if total_new_messages > 0:
            # Отправляем статус на клиент
            self.send(text_data=json.dumps({
                'type': 'status',
                'message': f'Ожидается получение {total_new_messages} сообщений...'
            }))

            for index, message in enumerate(filtered_messages):
                received_date_django_format = message['received_date_obj'].strftime('%Y-%m-%d %H:%M:%S%z')
                sent_date_cleaned = message['sent_date'].replace(' (UTC)', '').strip()
                sent_date_django_format = datetime.strptime(sent_date_cleaned, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S%z')

                # Сохраняем сообщение с вложениями
                email_message = EmailMessage.objects.create(
                    email_account=email_account,
                    subject=message['subject'],
                    sent_date=sent_date_django_format,
                    received_date=received_date_django_format,
                    body=message['body'],
                    attachments=message['attachments'],
                    uid=message['uid']  # Сохраняем UID сообщения
                )

                messages_added += 1

                # Отправляем сообщение на клиент
                self.send(text_data=json.dumps({
                    'type': 'progress',
                    'progress': f'{messages_added} / {total_new_messages}',
                    'status': f'Fetched {messages_added} of {total_new_messages} messages'
                }))

                self.send(text_data=json.dumps({
                    'type': 'message',
                    'id': email_message.id,
                    'subject': email_message.subject,
                    'sent_date': email_message.sent_date,
                    'received_date': email_message.received_date,
                    'body': email_message.body[:50],
                    'attachments': email_message.attachments
                }))

                # Обновляем клиент о текущем статусе
                remaining_messages = total_new_messages - (index + 1)
                self.send(text_data=json.dumps({
                    'type': 'status',
                    'message': f'Осталось получить {remaining_messages} сообщений...'
                }))

                sleep(0.01)

        if messages_added == 0:
            self.send(text_data=json.dumps({
                'type': 'complete',
                'status': 'Новых сообщений нет.'
            }))
        else:
            self.send(text_data=json.dumps({
                'type': 'complete',
                'status': 'Все новые сообщения успешно загружены!'
            }))
