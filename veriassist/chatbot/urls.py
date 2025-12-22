from django.urls import path

from . import views

urlpatterns = [
    path('',views.chatbot_index,name='chatbot_index'),
    path('chat/', views.chat_api, name='chat_api'), 

]