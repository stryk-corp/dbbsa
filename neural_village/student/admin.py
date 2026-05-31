from django.contrib import admin

from .models import ChatMessage


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'cohort', 'message_type', 'created_at')
    list_filter = ('message_type', 'cohort')
    search_fields = ('sender__user__username', 'sender__first_name', 'sender__last_name', 'content')
    readonly_fields = ('created_at',)
    raw_id_fields = ('sender', 'cohort')


admin.site.register(ChatMessage, ChatMessageAdmin)
