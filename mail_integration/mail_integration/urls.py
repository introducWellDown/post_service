from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from mail import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('messages/', views.list_messages, name='list_messages'),
    path('api/messages/', views.get_all_messages, name='get_all_messages'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

