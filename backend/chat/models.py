import uuid

from django.db import models


class ChatSession(models.Model):
    """Anonymous session (store id in browser). Swap to Supabase Auth user FK later."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=120, blank=True)
    country_code = models.CharField(max_length=8, default="SE")
    phone_e164 = models.CharField(
        max_length=20,
        blank=True,
        help_text="E.164 for Twilio nudges, e.g. +46701234567",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ChatMessage(models.Model):
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="message_rows"
    )
    role = models.CharField(max_length=16)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class UserProgress(models.Model):
    """Agentic memory: streak + free-form summary for cross-session personalization."""

    session = models.OneToOneField(
        ChatSession, on_delete=models.CASCADE, related_name="progress"
    )
    days_clean = models.PositiveIntegerField(null=True, blank=True)
    summary = models.TextField(
        blank=True,
        help_text="Short running summary for the model (e.g. last milestone mentioned).",
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
