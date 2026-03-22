"""
Research models.
"""
from django.db import models


class ResearchHistory(models.Model):
    """Persists every completed research run from the LangGraph pipeline."""

    topic = models.CharField(max_length=500)
    run_id = models.CharField(max_length=64, unique=True, blank=True, default="")

    # Core output fields (also stored in full inside final_report)
    overview = models.TextField(blank=True)
    key_concepts = models.JSONField(default=list)
    important_findings = models.JSONField(default=list)
    summary = models.TextField(blank=True)

    # Quality metadata
    confidence_score = models.FloatField(default=0.0)

    # Full structured report — single source of truth for the frontend
    final_report = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Research Histories"

    def __str__(self):
        return f"[{self.run_id[:8]}] {self.topic[:60]}"
