from django.urls import path

from .payment_views import payment_webhook

app_name = 'api_public'

urlpatterns = [
    path('webhooks/payments/', payment_webhook, name='payment_webhook'),
]
