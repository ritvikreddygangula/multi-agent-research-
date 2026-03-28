"""
URL configuration for research app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.conduct_research, name='conduct_research'),
    path('stream/', views.conduct_research_streaming, name='conduct_research_streaming'),
    path('budget/', views.token_budget, name='token_budget'),
    path('history/', views.history_list, name='history_list'),
    path('history/<int:pk>/', views.history_detail, name='history_detail'),
]
