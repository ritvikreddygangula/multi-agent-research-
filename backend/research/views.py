"""
Research views for handling research requests.
"""
import json
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from research.services.research_service import LangGraphResearchService

logger = logging.getLogger(__name__)

# Maps each LangGraph node to a (progress_start, progress_end, label) tuple.
# Used to emit backwards-compatible "progress" events alongside native node_update payloads.
_NODE_PROGRESS = {
    "planner":       (5,  18, "Planner: decomposing topic into sub-questions"),
    "rag_retrieval": (18, 25, "RAG: retrieving prior context from Pinecone"),
    "branch_0":      (25, 36, "Branch 0: researching sub-question"),
    "branch_1":      (36, 46, "Branch 1: researching sub-question"),
    "branch_2":      (46, 55, "Branch 2: researching sub-question"),
    "branch_3":      (55, 62, "Branch 3: researching sub-question"),
    "branch_4":      (62, 68, "Branch 4: researching sub-question"),
    "aggregator":    (68, 78, "Aggregator: merging branch findings"),
    "critic":        (78, 86, "Critic: evaluating synthesis quality"),
    "synthesizer":   (86, 98, "Synthesizer: generating final report"),
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conduct_research(request):
    """
    Non-streaming research endpoint — runs the full LangGraph pipeline and
    returns the final report in one response.

    Expected request body: { "topic": "..." }
    """
    topic = request.data.get('topic')

    if not topic or not isinstance(topic, str) or not topic.strip():
        return Response({'error': 'Topic must be a non-empty string.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        result = LangGraphResearchService().invoke(topic.strip())
        return Response({
            "topic":               result.get("topic", topic),
            "overview":            result.get("executive_summary", result.get("overview", "")),
            "key_concepts":        result.get("key_concepts", []),
            "important_findings":  result.get("important_findings", []),
            "summary":             result.get("summary", ""),
            "confidence_score":    result.get("confidence_score", 0.0),
            "sources":             result.get("sources", []),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("conduct_research failed for topic=%r", topic)
        return Response({'error': f'Research failed: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def event_stream_generator(topic: str):
    """
    Wraps LangGraphResearchService.stream() into SSE-formatted chunks.

    Each chunk is a JSON object with:
      • All fields from the LangGraph node_update/complete event
      • Extra "agent", "status", "message", "progress" fields for
        backwards compatibility with the current frontend progress bar.
    """
    try:
        logger.info("[sse] starting stream for topic=%r", topic)
        service = LangGraphResearchService()

        for event in service.stream(topic):
            event_type = event.get("type")

            if event_type == "node_update":
                node = event.get("node", "")
                prog_start, prog_end, label = _NODE_PROGRESS.get(node, (0, 0, node))
                payload = {
                    **event,
                    "agent":    node,
                    "status":   "completed",
                    "message":  label,
                    "progress": prog_end,
                }
                logger.debug("[sse] node_update node=%s progress=%d", node, prog_end)

            elif event_type == "complete":
                payload = {**event, "progress": 100}
                logger.info("[sse] complete event received")

            else:
                payload = event

            yield f"data: {json.dumps(payload)}\n\n"

    except Exception as e:
        import traceback
        logger.exception("[sse] stream error for topic=%r", topic)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'traceback': traceback.format_exc()})}\n\n"


@csrf_exempt
def conduct_research_streaming(request):
    """
    SSE endpoint for real-time LangGraph pipeline updates.

    CORS is handled entirely by django-cors-headers middleware (configured in
    settings.py). DO NOT add manual Access-Control-* headers here — doing so
    creates duplicate headers that browsers reject, breaking the SSE stream.

    Expected POST body: { "topic": "..." }
    Returns: text/event-stream of node_update and complete events.
    """
    if request.method == 'OPTIONS':
        # django-cors-headers handles preflight; this branch is a safety net.
        return JsonResponse({})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Manual JWT auth (DRF decorators can't be mixed with StreamingHttpResponse)
    auth = JWTAuthentication()
    try:
        auth_result = auth.authenticate(request)
        if auth_result is None:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        user, token = auth_result
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
        event_stream_generator(topic.strip()),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
