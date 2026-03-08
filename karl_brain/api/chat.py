"""
WebSocket /ws/chat — streaming de la conversation avec Karl.
POST /api/chat — version HTTP simple (sans streaming).
"""
import json
from typing import List, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.security import get_current_user
from core.database import get_db, Conversation, Message
from ai.claude_client import run_conversation, serialize_messages_for_db, deserialize_messages_from_db

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int


async def _load_conversation_messages(
    conversation_id: int, db: AsyncSession
) -> List[Dict[str, Any]]:
    """Charge l'historique d'une conversation depuis la DB."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    msgs = result.scalars().all()
    messages = []
    for msg in msgs:
        if msg.role in ("user", "assistant"):
            content = msg.content
            if msg.tool_calls:
                content = msg.tool_calls  # contenu riche (blocs)
            messages.append({"role": msg.role, "content": content})
    return messages


async def _save_message(
    conversation_id: int,
    role: str,
    content: str,
    tool_calls: Any,
    db: AsyncSession,
):
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content if isinstance(content, str) else str(content),
        tool_calls=tool_calls if isinstance(tool_calls, (list, dict)) else None,
    )
    db.add(msg)
    await db.flush()


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket pour le chat en temps réel.

    Protocole:
    - Client envoie: {"message": "...", "conversation_id": null|int, "token": "jwt..."}
    - Serveur stream:
        {"type": "text", "content": "..."}           — tokens texte
        {"type": "tool_start", "tool": "...", "input": {...}} — début appel outil
        {"type": "tool_end", "tool": "...", "result": {...}}  — fin appel outil
        {"type": "thinking", "content": "..."}        — réflexion Claude
        {"type": "done", "conversation_id": int}      — fin
        {"type": "error", "message": "..."}           — erreur
    """
    await websocket.accept()

    try:
        # ── Recevoir le premier message (auth + prompt) ─────────────────────────
        raw = await websocket.receive_text()
        data = json.loads(raw)

        # Vérifier le token JWT
        from core.security import decode_token
        token = data.get("token", "")
        if not token:
            await websocket.send_json({"type": "error", "message": "Authentication required"})
            await websocket.close(code=4001)
            return

        try:
            payload = decode_token(token)
        except Exception:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close(code=4001)
            return

        user_message = data.get("message", "").strip()
        if not user_message:
            await websocket.send_json({"type": "error", "message": "Empty message"})
            return

        conversation_id = data.get("conversation_id")

        # ── Créer ou charger la conversation ────────────────────────────────────
        if conversation_id:
            messages = await _load_conversation_messages(conversation_id, db)
        else:
            conv = Conversation(title=user_message[:100])
            db.add(conv)
            await db.flush()
            conversation_id = conv.id
            messages = []

        # Sauvegarder le message utilisateur
        await _save_message(conversation_id, "user", user_message, None, db)
        await db.commit()

        # Ajouter à l'historique
        messages.append({"role": "user", "content": user_message})

        # ── Callbacks de streaming ───────────────────────────────────────────────
        async def on_text(chunk: str):
            await websocket.send_json({"type": "text", "content": chunk})

        async def on_tool_start(tool_name: str, tool_input: dict):
            await websocket.send_json({
                "type": "tool_start",
                "tool": tool_name,
                "input": tool_input,
            })

        async def on_tool_end(tool_name: str, result: Any):
            result_str = result if isinstance(result, str) else json.dumps(result, default=str)
            await websocket.send_json({
                "type": "tool_end",
                "tool": tool_name,
                "result": result_str[:500],  # Tronquer pour l'UI
            })

        async def on_thinking(chunk: str):
            await websocket.send_json({"type": "thinking", "content": chunk})

        # ── Exécuter la conversation ─────────────────────────────────────────────
        final_text, updated_messages = await run_conversation(
            messages=messages,
            on_text=on_text,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
            on_thinking=on_thinking,
        )

        # ── Sauvegarder la réponse ──────────────────────────────────────────────
        serialized = serialize_messages_for_db(updated_messages)
        # La dernière réponse assistant
        last_assistant = None
        for msg in reversed(serialized):
            if msg["role"] == "assistant":
                last_assistant = msg
                break

        if last_assistant:
            content = last_assistant["content"]
            text_content = final_text
            rich_content = content if isinstance(content, list) else None
            await _save_message(conversation_id, "assistant", text_content, rich_content, db)
            await db.commit()

        # ── Envoyer la fin ──────────────────────────────────────────────────────
        await websocket.send_json({
            "type": "done",
            "conversation_id": conversation_id,
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.post("/api/chat", response_model=ChatResponse)
async def http_chat(
    request: ChatRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Version HTTP simple (sans streaming) pour les tests."""
    conversation_id = request.conversation_id

    if conversation_id:
        messages = await _load_conversation_messages(conversation_id, db)
    else:
        conv = Conversation(title=request.message[:100])
        db.add(conv)
        await db.flush()
        conversation_id = conv.id
        messages = []

    await _save_message(conversation_id, "user", request.message, None, db)
    messages.append({"role": "user", "content": request.message})

    final_text, updated_messages = await run_conversation(messages=messages)

    await _save_message(conversation_id, "assistant", final_text, None, db)
    await db.commit()

    return ChatResponse(reply=final_text, conversation_id=conversation_id)
