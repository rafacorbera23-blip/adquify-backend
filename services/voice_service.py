"""
Adquify Voice Service
======================
Servicio de voz para consultas al catálogo mediante audio.

Usa:
- OpenAI Whisper para transcripción (speech-to-text)
- gTTS o ElevenLabs para síntesis (text-to-speech)
"""

import os
import logging
from typing import Optional, Tuple
from io import BytesIO
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai not installed. Voice transcription disabled.")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. Voice synthesis disabled.")


class VoiceService:
    """Servicio de procesamiento de voz para Adquify"""
    
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
        
        if OPENAI_AVAILABLE and self.openai_key:
            self.openai_client = openai.AsyncOpenAI(api_key=self.openai_key)
            logger.info("✅ OpenAI Whisper configured")
        else:
            self.openai_client = None
            logger.warning("⚠️ OpenAI not configured for voice")
    
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "es"
    ) -> Optional[str]:
        """
        Transcribe audio to text using OpenAI Whisper
        
        Args:
            audio_bytes: Raw audio data
            filename: Filename with extension for format detection
            language: Language hint (es, en, etc.)
        
        Returns:
            Transcribed text or None if failed
        """
        if not self.openai_client:
            logger.error("OpenAI client not available")
            return None
        
        try:
            # Create file-like object
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename
            
            # Call Whisper API
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
            
            text = response.text.strip()
            logger.info(f"🎤 Transcribed: {text[:50]}...")
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def synthesize_speech(
        self,
        text: str,
        language: str = "es",
        slow: bool = False
    ) -> Optional[bytes]:
        """
        Convert text to speech using gTTS
        
        Args:
            text: Text to synthesize
            language: Language code
            slow: Whether to speak slowly
        
        Returns:
            MP3 audio bytes or None if failed
        """
        if not GTTS_AVAILABLE:
            logger.error("gTTS not available")
            return None
        
        try:
            # Generate speech
            tts = gTTS(text=text, lang=language, slow=slow)
            
            # Save to bytes
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            logger.info(f"🔊 Synthesized: {text[:50]}...")
            return audio_buffer.read()
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return None
    
    async def synthesize_speech_elevenlabs(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    ) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs (higher quality)
        
        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
        
        Returns:
            MP3 audio bytes or None if failed
        """
        if not self.elevenlabs_key:
            logger.error("ElevenLabs API key not configured")
            return None
        
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.elevenlabs_key
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"🔊 ElevenLabs synthesized: {text[:50]}...")
                    return response.content
                else:
                    logger.error(f"ElevenLabs error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")
            return None
    
    async def process_voice_query(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        chat_engine = None
    ) -> Tuple[str, Optional[bytes]]:
        """
        Full voice query pipeline:
        1. Transcribe audio to text
        2. Process query through chat engine
        3. Synthesize response to audio
        
        Args:
            audio_bytes: Input audio
            filename: Audio filename
            chat_engine: AdquifyChatEngine instance
        
        Returns:
            Tuple of (text_response, audio_response)
        """
        # Step 1: Transcribe
        text_query = await self.transcribe_audio(audio_bytes, filename)
        
        if not text_query:
            error_msg = "No pude entender el audio. ¿Puedes repetir?"
            return error_msg, self.synthesize_speech(error_msg)
        
        # Step 2: Process query
        if chat_engine:
            try:
                result = chat_engine.process_query(text_query)
                text_response = result.get("response", "No encontré información.")
            except Exception as e:
                logger.error(f"Chat engine error: {e}")
                text_response = f"Buscaste: {text_query}. Hubo un error procesando la consulta."
        else:
            text_response = f"Entendí: {text_query}. El motor de chat no está disponible."
        
        # Step 3: Synthesize response
        # Use ElevenLabs if available, otherwise gTTS
        if self.elevenlabs_key:
            audio_response = await self.synthesize_speech_elevenlabs(text_response)
        else:
            audio_response = self.synthesize_speech(text_response)
        
        return text_response, audio_response
    
    def is_available(self) -> dict:
        """Check what voice capabilities are available"""
        return {
            "transcription": bool(self.openai_client),
            "synthesis_gtts": GTTS_AVAILABLE,
            "synthesis_elevenlabs": bool(self.elevenlabs_key),
            "fully_functional": bool(self.openai_client) and (GTTS_AVAILABLE or self.elevenlabs_key)
        }


# ========== GLOBAL INSTANCE ==========

voice_service = VoiceService()


def get_voice_service() -> VoiceService:
    """Get the global voice service instance"""
    return voice_service
