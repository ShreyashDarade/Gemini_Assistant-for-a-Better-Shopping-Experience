"""
Chat API router with REST and WebSocket endpoints.
"""

import contextlib
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ErrorResponse,
)
from app.services.ai_engine import get_ai_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Send a chat message",
    description="Process a user message and return AI response with products/media",
)
async def chat(
    request: ChatRequest,
    x_session_id: str | None = Header(
        default=None, alias="X-Session-ID", description="Session ID for conversation continuity"
    ),
    x_user_id: str | None = Header(
        default=None, alias="X-User-ID", description="Optional user identifier"
    ),
):
    """
    Process user message through AI pipeline.

    **Flow:**
    1. Intent classification (what does the user want?)
    2. Entity extraction (products, prices, categories mentioned)
    3. Response generation (search products, generate text)
    4. Context update (save for conversation continuity)

    **Headers:**
    - `X-Session-ID`: Pass to maintain conversation context
    - `X-User-ID`: Optional user identifier for personalization
    """
    try:
        ai_engine = get_ai_engine()

        result = await ai_engine.process_query(
            query=request.message, session_id=x_session_id, user_id=x_user_id
        )

        if not result.get("success"):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "Failed to process message",
                    "session_id": result.get("session_id"),
                },
            )

        response_data = result.get("response", {})

        return ChatResponse(
            success=True,
            session_id=result.get("session_id", ""),
            message=response_data.get("message", ""),
            intent=response_data.get("intent", "unknown"),
            intent_confidence=response_data.get("intent_confidence", 0),
            products=response_data.get("products", []),
            media=response_data.get("media", []),
            comparison=response_data.get("comparison"),
            suggestions=response_data.get("suggestions", []),
            processing_time_ms=response_data.get("processing_time_ms", 0),
        )

    except Exception as e:
        logger.exception(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket, session_id: str | None = None, user_id: str | None = None
):
    """
    WebSocket endpoint for real-time chat.

    **Connection:**
    ws://host/api/v1/chat/ws?session_id=xxx&user_id=yyy

    **Message format (send):**
    ```json
    {"message": "Your query here"}
    ```

    **Message format (receive):**
    ```json
    {
        "type": "response",
        "session_id": "xxx",
        "message": "AI response",
        "products": [...],
        ...
    }
    ```
    """
    await websocket.accept()

    ai_engine = get_ai_engine()
    current_session_id = session_id

    try:
        # Send connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": current_session_id,
                "message": "Connected to Shopping Assistant",
            }
        )

        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "").strip()

                if not user_message:
                    await websocket.send_json({"type": "error", "error": "Empty message"})
                    continue

                # Send processing indicator
                await websocket.send_json(
                    {"type": "processing", "message": "Processing your request..."}
                )

                # Process query
                result = await ai_engine.process_query(
                    query=user_message, session_id=current_session_id, user_id=user_id
                )

                # Update session ID if new
                if result.get("session_id"):
                    current_session_id = result["session_id"]

                # Send response
                response_data = result.get("response", {})
                await websocket.send_json(
                    {
                        "type": "response",
                        "session_id": current_session_id,
                        "success": result.get("success", True),
                        **response_data,
                    }
                )

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON format"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={current_session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "error": "Internal error"})


@router.get(
    "/sessions/{session_id}",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Retrieve conversation history for a session",
)
async def get_session_history(session_id: str, limit: int = Query(default=20, ge=1, le=100)):
    """Get conversation history for a session."""
    try:
        ai_engine = get_ai_engine()
        history = await ai_engine.get_session_history(session_id, limit)

        return ConversationHistoryResponse(**history)

    except Exception as e:
        logger.exception(f"Get history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.delete(
    "/sessions/{session_id}",
    summary="Clear conversation",
    description="Clear conversation history for a session",
)
async def clear_session(session_id: str):
    """Clear conversation history."""
    try:
        ai_engine = get_ai_engine()
        await ai_engine.clear_session(session_id)

        return {"success": True, "message": "Session cleared"}

    except Exception as e:
        logger.exception(f"Clear session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e
