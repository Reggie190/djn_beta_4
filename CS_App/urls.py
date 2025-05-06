from django.urls import path
from . import views
from .views import chat_view, send_message, chat_api,login_view,register_view,line_webhook   # 確保有匯入 send_message
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', chat_view, name='chat'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='chat'), name='logout'),
    path('register/', views.register_view, name='register'), 
    path('line/webhook/', line_webhook, name='line_webhook'),
    path('chat/', chat_view, name='chat'),
    path('send_message/', send_message, name='send_message'), # type: ignore
    path('chat_api/', chat_api, name='chat_api'), # type: ignore
]