import json
import os
import uuid

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .agent import anthropic_agent_turn
from .llm import complete
from .models import ChatMessage, ChatSession, UserProgress
from .rag import retrieve_relevant_chunks


def _memory_block(progress: UserProgress | None) -> str:
    if not progress:
        return ""
    lines = []
    if progress.days_clean is not None:
        lines.append(f"- Reported gamble-free streak: {progress.days_clean} day(s).")
    if progress.summary:
        lines.append(f"- Notes from prior sessions:\n{progress.summary[:1200]}")
    if not lines:
        return ""
    return "USER MEMORY (from database — use naturally, do not read verbatim as a list):\n" + "\n".join(
        lines
    )


@csrf_exempt
@require_GET
def session_detail(request, session_id):
    try:
        sid = uuid.UUID(str(session_id))
    except ValueError:
        return JsonResponse({"error": "invalid session id"}, status=400)
    try:
        session = ChatSession.objects.get(id=sid)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    msgs = [
        {"role": m.role, "content": m.content}
        for m in session.message_rows.order_by("created_at")
    ]
    prog = getattr(session, "progress", None)
    progress_payload = None
    if prog:
        progress_payload = {
            "days_clean": prog.days_clean,
            "summary": prog.summary[:2000] if prog.summary else "",
        }
    return JsonResponse(
        {
            "session_id": str(session.id),
            "display_name": session.display_name,
            "country_code": session.country_code,
            "messages": msgs,
            "progress": progress_payload,
        }
    )


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

    display_name = (body.get("display_name") or "")[:120]
    country_code = (body.get("country_code") or "SE")[:8]
    raw_sid = body.get("session_id")

    session = None
    if raw_sid:
        try:
            session = ChatSession.objects.get(id=uuid.UUID(str(raw_sid)))
        except (ValueError, ChatSession.DoesNotExist):
            session = None

    if session is None:
        session = ChatSession.objects.create(
            display_name=display_name,
            country_code=country_code,
        )
    else:
        if display_name and session.display_name != display_name:
            session.display_name = display_name
        if country_code and session.country_code != country_code:
            session.country_code = country_code
        session.save()

    prog, _ = UserProgress.objects.get_or_create(session=session)
    memory = _memory_block(prog)

    last_user = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user = str(m.get("content") or "")
            break
    rag_text = retrieve_relevant_chunks(last_user)
    rag_block = ""
    if rag_text:
        rag_block = (
            "\n\n## Retrieved legal / regulatory excerpts (cite when relevant)\n"
            + rag_text
        )

    augmented_system = system + rag_block
    if memory:
        augmented_system += "\n\n## Persistent memory\n" + memory

    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()

    try:
        if provider == "anthropic" and os.environ.get("AGENT_TOOLS", "1") == "1":
            text = anthropic_agent_turn(
                augmented_system, messages, session_id=str(session.id)
            )
        else:
            text = complete(augmented_system, messages)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=500)
    except RuntimeError as e:
        return JsonResponse({"error": str(e)}, status=502)

    ChatMessage.objects.filter(session=session).delete()
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            ChatMessage.objects.create(session=session, role=role, content=content)
    ChatMessage.objects.create(session=session, role="assistant", content=text)

    prog.last_message_at = timezone.now()
    prog.save()

    return JsonResponse({"text": text, "session_id": str(session.id)})
