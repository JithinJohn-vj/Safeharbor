import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .llm import complete


@csrf_exempt
@require_POST
def chat(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    system = body.get("system")
    messages = body.get("messages")
    if not isinstance(system, str) or not isinstance(messages, list):
        return JsonResponse(
            {"error": "Expected { system: string, messages: array }"},
            status=400,
        )

    try:
        text = complete(system, messages)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=500)
    except RuntimeError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse({"text": text})
