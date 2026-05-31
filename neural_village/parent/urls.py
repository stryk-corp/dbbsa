from django.urls import path
from .views import dashboard, students, progress

app_name = 'parent'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('students/', students, name='students'),
    path('progress/', progress, name='progress'),
]
