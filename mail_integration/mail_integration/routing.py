from django.urls import re_path
from mail.consumers import MailConsumer

websocket_urlpatterns = [
    re_path(r'ws/messages/$', MailConsumer.as_asgi()),
]
