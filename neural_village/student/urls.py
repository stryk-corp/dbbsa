from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('', views.home, name='home'),
    path('', views.home, name='dashboard'),
    path('assignments/', views.assignments, name='assignments'),
    path('live-quizzes/', views.live_quizzes, name='live_quizzes'),
    path('live-quizzes/start/<uuid:quiz_id>/', views.start_live_quiz, name='start_live_quiz'),
    path('results/', views.results, name='results'),
    path('live-class/', views.live_class, name='live_class'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/send/', views.chat_send, name='chat_send'),
    path('chat/poll/', views.chat_poll, name='chat_poll'),
    path('courses/', views.courses, name='courses'),
    path('webrtc/offer/', views.webrtc_offer, name='webrtc_offer'),
    path('webrtc/ice-candidate/', views.webrtc_ice_candidate, name='webrtc_ice_candidate'),
    path('webrtc/close/', views.webrtc_close, name='webrtc_close'),
]
