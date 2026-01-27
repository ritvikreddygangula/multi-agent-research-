"""
Research views for handling research requests.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from research.services.research_service import ResearchService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conduct_research(request):
    """
    Endpoint to conduct multi-agent research on a topic.
    
    Expected request body:
    {
        "topic": "Research topic string"
    }
    
    Returns structured research results.
    """
    topic = request.data.get('topic')
    
    if not topic:
        return Response(
            {'error': 'Topic is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not isinstance(topic, str) or len(topic.strip()) == 0:
        return Response(
            {'error': 'Topic must be a non-empty string.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        research_service = ResearchService()
        result = research_service.conduct_research(topic.strip())
        
        # Return structured result matching frontend expectations
        return Response({
            "topic": result["topic"],
            "overview": result["overview"],
            "key_concepts": result["key_concepts"],
            "important_findings": result["important_findings"],
            "summary": result["summary"]
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Research failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
