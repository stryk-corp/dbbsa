from django.urls import path
from .views import dashboard, students, progress, financials, initialize_payment

app_name = 'parent'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('students/', students, name='students'),
    path('progress/', progress, name='progress'),
    path('financials/', financials, name='financials'),
    path('financials/pay/', initialize_payment, name='initialize_payment'),
]
