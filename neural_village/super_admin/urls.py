from django.urls import path
from .views import dashboard

app_name = 'super_admin'

urlpatterns = [
    path('', dashboard, name='dashboard'),
]
