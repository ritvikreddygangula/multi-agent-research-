"""
Research views for handling research requests.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from research.services.research_service import ResearchService
from research.services.research_service_streaming import StreamingResearchService


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


def event_stream_generator(topic):
    """Generator function that yields SSE formatted events."""
    import sys
    
    try:
        print(f"🔵 Starting streaming research for: {topic}", flush=True)
        service = StreamingResearchService()
        
        for update in service.conduct_research_streaming(topic):
            # Format as SSE - ensure proper formatting
            data = json.dumps(update)
            sse_message = f"data: {data}\n\n"
            print(f"📤 Sending SSE update: {update.get('type')} - {update.get('agent', 'N/A')} - {update.get('progress', 0)}%", flush=True)
            yield sse_message
            # Flush immediately to ensure data is sent
            sys.stdout.flush()
            
    except Exception as e:
        import traceback
        print(f"❌ Stream error: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        error_data = json.dumps({
            "type": "error",
            "message": f"Stream error: {str(e)}",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        yield f"data: {error_data}\n\n"


@csrf_exempt
def conduct_research_streaming(request):
    """
    Endpoint to conduct multi-agent research with streaming updates.
    Bypasses DRF to avoid content negotiation issues with SSE.
    
    Expected request body:
    {
        "topic": "Research topic string"
    }
    
    Returns Server-Sent Events stream with progress updates.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
        return response
    
    if request.method != 'POST':
        response = JsonResponse({'error': 'Method not allowed'}, status=405)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        return response
    
    # Manual JWT authentication
    auth = JWTAuthentication()
    try:
        auth_result = auth.authenticate(request)
        if auth_result is None:
            response = JsonResponse({'error': 'Authentication required'}, status=401)
            origin = request.headers.get('Origin')
            if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
                response['Access-Control-Allow-Origin'] = origin
            return response
        user, token = auth_result
    except Exception as e:
        response = JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=401)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        return response
    
    # Parse request body
    try:
        import json as json_lib
        body = json_lib.loads(request.body)
        topic = body.get('topic')
    except (json_lib.JSONDecodeError, AttributeError, TypeError) as e:
        response = JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        return response
    
    if not topic:
        response = JsonResponse({'error': 'Topic is required.'}, status=400)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        return response
    
    if not isinstance(topic, str) or len(topic.strip()) == 0:
        response = JsonResponse({'error': 'Topic must be a non-empty string.'}, status=400)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
            response['Access-Control-Allow-Origin'] = origin
        return response
    
    # Stream the actual research (no initial message needed - backend sends updates immediately)
    def event_stream_with_initial():
        # Stream the actual research
        for chunk in event_stream_generator(topic.strip()):
            yield chunk
    
    response = StreamingHttpResponse(
        event_stream_with_initial(), 
        content_type='text/event-stream; charset=utf-8'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering in nginx
    response['Connection'] = 'keep-alive'
    # CORS headers
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
        response['Access-Control-Allow-Origin'] = origin
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response
