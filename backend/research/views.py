"""
Research views — research endpoints + CRUD history management.
"""
import json
import logging

from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from research.services.research_service import ResearchService
from research.services.research_service_streaming import StreamingResearchService
from research.models import ResearchHistory
from research.serializers import ResearchHistorySerializer

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_run(user, result: dict):
    """Persist a completed research run for the given user."""
    try:
        ResearchHistory.objects.create(
            user=user,
            run_id=result.get('run_id', ''),
            topic=result.get('topic', ''),
            executive_summary=result.get('executive_summary') or result.get('overview', ''),
            key_concepts=result.get('key_concepts', []),
            important_findings=result.get('important_findings', []),
            summary=result.get('summary', ''),
            sources=result.get('sources', []),
            confidence_score=result.get('confidence_score'),
        )
    except Exception:
        logger.exception("Failed to save research run for user=%s", user)


# ── Research endpoints ─────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conduct_research(request):
    topic = request.data.get('topic')
    if not topic or not isinstance(topic, str) or not topic.strip():
        return Response({'error': 'Topic must be a non-empty string.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        result = ResearchService().conduct_research(topic.strip())
        _save_run(request.user, result)
        return Response({
            'topic':              result.get('topic', topic),
            'overview':           result.get('overview', ''),
            'key_concepts':       result.get('key_concepts', []),
            'important_findings': result.get('important_findings', []),
            'summary':            result.get('summary', ''),
            'confidence_score':   result.get('confidence_score', 0.0),
            'sources':            result.get('sources', []),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("conduct_research failed for topic=%r", topic)
        return Response({'error': f'Research failed: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _event_stream_generator(topic: str, user):
    """Wrap StreamingResearchService into SSE chunks and auto-save on complete."""
    try:
        service = StreamingResearchService()
        for event in service.conduct_research_streaming(topic):
            if event.get('type') == 'complete':
                _save_run(user, event)
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:
        import traceback
        logger.exception("[sse] stream error for topic=%r", topic)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'traceback': traceback.format_exc()})}\n\n"


@csrf_exempt
def conduct_research_streaming(request):
    if request.method == 'OPTIONS':
        return JsonResponse({})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    auth = JWTAuthentication()
    try:
        auth_result = auth.authenticate(request)
        if auth_result is None:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        user, _token = auth_result
    except Exception as e:
        return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=401)

    try:
        body = json.loads(request.body)
        topic = body.get('topic')
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)

    if not topic or not isinstance(topic, str) or not topic.strip():
        return JsonResponse({'error': 'Topic must be a non-empty string.'}, status=400)

    response = StreamingHttpResponse(
        _event_stream_generator(topic.strip(), user),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── History CRUD ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history_list(request):
    """GET /api/research/history/ — list all runs for the current user."""
    runs = ResearchHistory.objects.filter(user=request.user)
    serializer = ResearchHistorySerializer(runs, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def history_detail(request, pk):
    run = get_object_or_404(ResearchHistory, pk=pk, user=request.user)

    if request.method == 'GET':
        return Response(ResearchHistorySerializer(run).data)

    if request.method == 'PATCH':
        new_topic = request.data.get('topic', '').strip()
        if not new_topic:
            return Response({'error': 'topic is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run.topic = new_topic
        run.save(update_fields=['topic'])
        return Response(ResearchHistorySerializer(run).data)

    if request.method == 'DELETE':
        run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
