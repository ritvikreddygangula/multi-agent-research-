"""
URL configuration for research app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.conduct_research, name='conduct_research'),
]
