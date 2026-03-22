from django.db import models


class ResearchHistory(models.Model):
    """Persists every completed research run from the LangGraph pipeline."""

    topic = models.CharField(max_length=500)
    run_id = models.CharField(max_length=64, unique=True, blank=True, default="")
    overview = models.TextField(blank=True)
    key_concepts = models.JSONField(default=list)
    important_findings = models.JSONField(default=list)
    summary = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0)
    final_report = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Research Histories"

    def __str__(self):
        return f"[{self.run_id[:8]}] {self.topic[:60]}"
