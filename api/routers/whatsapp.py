from fastapi import APIRouter, Request, HTTPException, Query, Response, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import logging
import httpx
import json
from core.database import SessionLocal
from services.chat_engine import AdquifyChatEngine

router = APIRouter(
    prefix="/api/whatsapp",
    tags=["WhatsApp"]
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "adquify_verify_token")
API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

async def send_whatsapp_message(to: str, text: str):
    """
    Sends a message via WhatsApp Graph API.
    """
    if not API_TOKEN or not PHONE_NUMBER_ID:
        logger.error("❌ WhatsApp API Credentials missing (WHATSAPP_API_TOKEN or WHATSAPP_PHONE_NUMBER_ID)")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"✅ WhatsApp reply sent to {to}")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to send WhatsApp message: {e.response.text}")
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {e}")

async def process_message_background(sender_id: str, text: str):
    """
    Processes the message using RAG Engine and replies.
    Rens in background to avoid blocking the webhook.
    """
    logger.info(f"🤖 Processing message from {sender_id}: {text}")
    
    db = SessionLocal()
    try:
        # Initialize Chat Engine
        chat_engine = AdquifyChatEngine(db)
        
        # Get AI Response
        response = await chat_engine.process_query(text)
        answer = response.get("answer", "Lo siento, hubo un error procesando tu consulta.")
        pdf_url = response.get("pdf_url")
        
        # Format reply
        full_reply = answer
        if pdf_url:
            full_reply += f"\n\n📄 *PDF Generado:* {pdf_url}"
            
        # Send Reply
        await send_whatsapp_message(sender_id, full_reply)
        
    except Exception as e:
        logger.error(f"❌ Error in RAG processing: {e}")
        await send_whatsapp_message(sender_id, "Lo siento, tuve un problema interno consultando el catálogo.")
    finally:
        db.close()

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
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Receive messages from WhatsApp (and other events).
    """
    try:
        data = await request.json()
        
        # Log parsed brief for clarity
        # logger.info(f"📩 WhatsApp Payload: {json.dumps(data)}")

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
                            
                            if msg_type == "text":
                                logger.info(f"💬 Message from {sender_id}: {text}")
                                # Trigger background processing
                                background_tasks.add_task(process_message_background, sender_id, text)
                            else:
                                logger.info(f"Ignored non-text message type: {msg_type}")

        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return {"status": "error", "message": str(e)}
