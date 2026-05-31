import uuid
from django.db import models
from neural_village.core.models import Student, Cohort


class ChatMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('voice', 'Voice Call'),
        ('video', 'Video Call'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='chat_messages')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='chat_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    content = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.user.username} ({self.message_type}) @ {self.created_at:%Y-%m-%d %H:%M}"
