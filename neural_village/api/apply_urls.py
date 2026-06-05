from django.urls import path
from .apply_views import (
    apply_start,
    initialize_application_payment,
    apply_continue,
    apply_details,
    check_application,
)

app_name = 'apply'

urlpatterns = [
    path('', apply_start, name='apply_start'),
    path('pay/', initialize_application_payment, name='initialize_application_payment'),
    path('continue/', apply_continue, name='apply_continue'),
    path('details/<uuid:token>/', apply_details, name='apply_details'),
    path('check/', check_application, name='check_application'),
    path('status/<uuid:token>/', check_application, name='check_application_token'),
]
