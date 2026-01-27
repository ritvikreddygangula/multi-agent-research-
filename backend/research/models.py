"""
Research models (optional - for future enhancements like saving research history).
"""
from django.db import models
from django.conf import settings


class ResearchHistory(models.Model):
    """Model to store research history (optional for future use)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic = models.CharField(max_length=500)
    overview = models.TextField()
    key_concepts = models.JSONField(default=list)
    important_findings = models.JSONField(default=list)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Research Histories'

    def __str__(self):
        return f"{self.user.email} - {self.topic[:50]}"
