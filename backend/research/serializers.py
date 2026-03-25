from rest_framework import serializers
from .models import ResearchHistory


class ResearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchHistory
        fields = [
            'id', 'run_id', 'topic', 'executive_summary',
            'key_concepts', 'important_findings', 'summary',
            'sources', 'confidence_score', 'created_at',
        ]
        read_only_fields = [
            'id', 'run_id', 'executive_summary', 'key_concepts',
            'important_findings', 'summary', 'sources',
            'confidence_score', 'created_at',
        ]
