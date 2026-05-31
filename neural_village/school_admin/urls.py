from django.urls import path
from .views import dashboard, cohorts, hardware, onboarding

app_name = 'school_admin'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('cohorts/', cohorts, name='cohorts'),
    path('hardware/', hardware, name='hardware'),
    path('onboarding/', onboarding, name='onboarding'),
]
