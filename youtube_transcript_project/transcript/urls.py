from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_notes/', views.get_notes, name='get_notes'),
    path('ask_question/', views.ask_question, name='ask_question'),
]
