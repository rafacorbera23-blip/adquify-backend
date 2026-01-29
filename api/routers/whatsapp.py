from fastapi import APIRouter, Request, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import logging

router = APIRouter(
    prefix="/api/whatsapp",
    tags=["WhatsApp"]
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "adquify_verify_token")

@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    """
    Webhook verification for Meta/WhatsApp.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WhatsApp Webhook Verified!")
        # Return the challenge as plain text (required by Meta)
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"❌ Webhook verification failed. Token: {token}, Mode: {mode}")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def receive_message(request: Request):
    """
    Receive messages from WhatsApp (and other events).
    """
    try:
        data = await request.json()
        
        # Log the full payload for debugging
        logger.info(f"📩 WhatsApp Payload: {data}")
        
        # Process entry
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    if "messages" in value:
                        for message in value["messages"]:
                            sender_id = message.get("from")
                            text = message.get("text", {}).get("body", "")
                            msg_type = message.get("type")
                            
                            logger.info(f"💬 Message from {sender_id} ({msg_type}): {text}")
                            
                            # TODO: Process message using Chat Engine
                            # notification_service.process_whatsapp_message(sender_id, text)
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return {"status": "error", "message": str(e)}
