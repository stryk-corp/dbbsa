from django.urls import path
from .views import cohorts, dashboard, cohort_detail, insights, school_overview, students, log_event

app_name = 'instructor'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('cohorts/', cohorts, name='cohorts'),
    path('students/', students, name='students'),
    path('insights/', insights, name='insights'),
    path('school/', school_overview, name='school_overview'),
    path('cohort/<uuid:cohort_id>/', cohort_detail, name='cohort_detail'),
    path('log-event/', log_event, name='log_event'),
]
