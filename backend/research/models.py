"""
Research models — persists completed research runs per user.
"""
import uuid
from django.conf import settings
from django.db import models


class ResearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_history')
    run_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    topic = models.CharField(max_length=500)
    executive_summary = models.TextField(blank=True, default='')
    key_concepts = models.JSONField(default=list)
    important_findings = models.JSONField(default=list)
    summary = models.TextField(blank=True, default='')
    sources = models.JSONField(default=list)
    confidence_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Research Histories"

    def __str__(self):
        return f"{self.user.email} — {self.topic[:60]}"
