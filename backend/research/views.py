"""
Research views — research endpoints + CRUD history management.
"""
import json
import logging
from django.conf import settings

from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import UserTokenBudget
from research.services.research_service import LangGraphResearchService
from research.models import ResearchHistory
from research.serializers import ResearchHistorySerializer

logger = logging.getLogger(__name__)


# ── Token budget helpers ────────────────────────────────────────────────────────

def _get_budget(user) -> UserTokenBudget:
    budget, _ = UserTokenBudget.objects.get_or_create(
        user=user,
        defaults={'token_limit': getattr(settings, 'DEFAULT_TOKEN_LIMIT', 100_000)},
    )
    return budget


def _budget_exceeded_response(budget: UserTokenBudget):
    return {
        'error': (
            f'You have used all {budget.token_limit:,} tokens in your research quota. '
            'Please contact the administrator to increase your limit.'
        ),
        'error_code': 'token_limit_exceeded',
        'tokens_used': budget.tokens_used,
        'token_limit': budget.token_limit,
    }


def _deduct_tokens(user, count: int) -> None:
    if count > 0:
        UserTokenBudget.objects.filter(user=user).update(tokens_used=F('tokens_used') + count)


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


_MAX_TOPIC_LENGTH = 500


def _validate_topic(topic) -> str | None:
    if not topic or not isinstance(topic, str):
        return None
    topic = topic.strip()
    if not topic or len(topic) > _MAX_TOPIC_LENGTH:
        return None
    return topic


# ── Research endpoints ─────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conduct_research(request):
    topic = _validate_topic(request.data.get('topic'))
    if not topic:
        return Response(
            {'error': f'Topic must be a non-empty string (max {_MAX_TOPIC_LENGTH} chars).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    budget = _get_budget(request.user)
    if budget.is_over_limit:
        return Response(_budget_exceeded_response(budget), status=status.HTTP_402_PAYMENT_REQUIRED)

    try:
        result = LangGraphResearchService().invoke(topic)
        _save_run(request.user, result)
        _deduct_tokens(request.user, result.get('tokens_used', 0))
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
        msg = str(e) if settings.DEBUG else 'Research failed. Please try again.'
        return Response({'error': msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _stream_generator(topic: str, user):
    """Run LangGraph and emit SSE events. Saves the run and deducts tokens on completion."""
    try:
        for event in LangGraphResearchService().stream(topic):
            if event.get('type') == 'complete':
                _save_run(user, event)
                _deduct_tokens(user, event.get('tokens_used', 0))
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:
        logger.exception("[sse] stream error for topic=%r", topic)
        payload = {'type': 'error', 'message': str(e)}
        if settings.DEBUG:
            import traceback
            payload['traceback'] = traceback.format_exc()
        yield f"data: {json.dumps(payload)}\n\n"


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
        user, _ = auth_result
    except Exception as e:
        return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=401)

    try:
        body = json.loads(request.body)
        topic = body.get('topic')
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)

    topic = _validate_topic(topic)
    if not topic:
        return JsonResponse(
            {'error': f'Topic must be a non-empty string (max {_MAX_TOPIC_LENGTH} chars).'},
            status=400,
        )

    budget = _get_budget(user)
    if budget.is_over_limit:
        return JsonResponse(_budget_exceeded_response(budget), status=402)

    response = StreamingHttpResponse(
        _stream_generator(topic, user),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── Budget status endpoint ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def token_budget(request):
    budget = _get_budget(request.user)
    return Response({
        'tokens_used':      budget.tokens_used,
        'token_limit':      budget.token_limit,
        'tokens_remaining': budget.tokens_remaining,
        'is_over_limit':    budget.is_over_limit,
    })


# ── History CRUD ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history_list(request):
    runs = ResearchHistory.objects.filter(user=request.user).order_by('-created_at')
    return Response(ResearchHistorySerializer(runs, many=True).data)


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
