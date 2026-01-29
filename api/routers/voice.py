"""
Adquify Voice API Router
=========================
Endpoints para consultas por voz.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from services.voice_service import get_voice_service
from services.chat_engine import AdquifyChatEngine
from core.database import SessionLocal

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status")
def voice_status():
    """Check voice service availability"""
    service = get_voice_service()
    return service.is_available()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "es"
):
    """
    Transcribe audio file to text
    
    Accepts: WAV, MP3, M4A, WEBM, OGG
    """
    service = get_voice_service()
    
    if not service.is_available()["transcription"]:
        raise HTTPException(
            status_code=503,
            detail="Transcription service not available. Set OPENAI_API_KEY."
        )
    
    content = await file.read()
    text = await service.transcribe_audio(content, file.filename, language)
    
    if text is None:
        raise HTTPException(status_code=500, detail="Transcription failed")
    
    return {"text": text}


@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    language: str = "es",
    use_elevenlabs: bool = False
):
    """
    Convert text to speech audio
    
    Returns: MP3 audio file
    """
    service = get_voice_service()
    
    if use_elevenlabs:
        audio = await service.synthesize_speech_elevenlabs(text)
    else:
        audio = service.synthesize_speech(text, language)
    
    if audio is None:
        raise HTTPException(status_code=500, detail="Speech synthesis failed")
    
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=response.mp3"}
    )


@router.post("/query")
async def voice_query(
    file: UploadFile = File(...),
    language: str = "es",
    return_audio: bool = True
):
    """
    Full voice query pipeline:
    1. Transcribe audio question
    2. Process with chat engine
    3. Return text + optional audio response
    """
    service = get_voice_service()
    
    if not service.is_available()["transcription"]:
        raise HTTPException(
            status_code=503,
            detail="Transcription service not available. Set OPENAI_API_KEY."
        )
    
    # Get chat engine
    db = SessionLocal()
    try:
        chat_engine = AdquifyChatEngine(db)
        
        # Process voice query
        content = await file.read()
        text_response, audio_response = await service.process_voice_query(
            audio_bytes=content,
            filename=file.filename,
            chat_engine=chat_engine
        )
        
        if return_audio and audio_response:
            # Return audio response
            return Response(
                content=audio_response,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "attachment; filename=response.mp3",
                    "X-Text-Response": text_response[:200]  # Include text in header
                }
            )
        else:
            return {"response": text_response}
    finally:
        db.close()
