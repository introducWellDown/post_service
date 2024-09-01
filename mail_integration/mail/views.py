from django.shortcuts import render
from django.http import JsonResponse
from .models import EmailMessage

def list_messages(request):
    return render(request, 'mail/list_messages.html')

def get_all_messages(request):
    # Получаем все сообщения из базы данных, отсортированные по дате получения (от новых к старым)
    messages = EmailMessage.objects.all().order_by('-received_date')
    messages_list = []
    
    for message in messages:
        messages_list.append({
            'id': message.id,
            'subject': message.subject,
            'sent_date': message.sent_date.strftime('%a, %d %b %Y %H:%M:%S %z'),
            'received_date': message.received_date.strftime('%a, %d %b %Y %H:%M:%S %z'),
            'body': message.body[:50],  # Отправляем только первые 50 символов текста сообщения
            'attachments': [attachment for attachment in message.attachments]  # Добавляем ссылки на вложения
        })
    
    return JsonResponse({'messages': messages_list})

