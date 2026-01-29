"""
Adquify Notification Service
=============================
Servicio de notificaciones para enviar alertas a usuarios vía Telegram, WhatsApp, etc.

Eventos:
- Nuevos productos añadidos
- Cambios de precio
- Scraper completado/fallido
- Reportes generados
"""

import os
import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    NEW_PRODUCTS = "new_products"
    PRICE_CHANGE = "price_change"
    SCRAPER_COMPLETE = "scraper_complete"
    SCRAPER_ERROR = "scraper_error"
    REPORT_READY = "report_ready"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationService:
    """Servicio centralizado de notificaciones"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_ids: List[str] = []  # Subscribers
        
        # Load subscribers from env or file
        subscribers = os.getenv("TELEGRAM_SUBSCRIBERS", "")
        if subscribers:
            self.telegram_chat_ids = [s.strip() for s in subscribers.split(",")]
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.notification_history: List[dict] = []
        
        self._initialized = True
        logger.info("✅ NotificationService initialized")
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
    # ========== TELEGRAM NOTIFICATIONS ==========
    
    async def send_telegram(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "Markdown"
    ) -> bool:
        """Send a message via Telegram"""
        if not self.telegram_token:
            logger.warning("Telegram token not configured")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = await self.http_client.post(url, json=payload)
            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def broadcast_telegram(self, message: str) -> int:
        """Send message to all Telegram subscribers"""
        sent = 0
        for chat_id in self.telegram_chat_ids:
            if await self.send_telegram(chat_id, message):
                sent += 1
        return sent
    
    def add_telegram_subscriber(self, chat_id: str):
        """Add a Telegram chat to subscribers"""
        if chat_id not in self.telegram_chat_ids:
            self.telegram_chat_ids.append(chat_id)
            logger.info(f"➕ Added Telegram subscriber: {chat_id}")
    
    def remove_telegram_subscriber(self, chat_id: str):
        """Remove a Telegram chat from subscribers"""
        if chat_id in self.telegram_chat_ids:
            self.telegram_chat_ids.remove(chat_id)
            logger.info(f"➖ Removed Telegram subscriber: {chat_id}")
    
    # ========== NOTIFICATION TYPES ==========
    
    async def notify_new_products(
        self,
        supplier: str,
        products: List[dict],
        channels: List[NotificationChannel] = None
    ):
        """Notify about new products added"""
        channels = channels or [NotificationChannel.TELEGRAM]
        
        count = len(products)
        sample = products[:3] if products else []
        
        message = f"""
🆕 *Nuevos Productos - {supplier}*

Se han añadido *{count}* nuevos productos al catálogo.

"""
        for p in sample:
            name = p.get("name", "Sin nombre")[:40]
            price = p.get("price", 0)
            message += f"• {name} - {price:.2f}€\n"
        
        if count > 3:
            message += f"\n_...y {count - 3} más_"
        
        message += f"\n\n🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        await self._send_to_channels(
            NotificationType.NEW_PRODUCTS,
            message,
            channels,
            {"supplier": supplier, "count": count}
        )
    
    async def notify_price_changes(
        self,
        changes: List[dict],
        channels: List[NotificationChannel] = None
    ):
        """Notify about price changes"""
        channels = channels or [NotificationChannel.TELEGRAM]
        
        message = f"""
💰 *Cambios de Precio Detectados*

Se han detectado *{len(changes)}* cambios de precio:

"""
        for change in changes[:5]:
            name = change.get("name", "Producto")[:30]
            old = change.get("old_price", 0)
            new = change.get("new_price", 0)
            diff = new - old
            emoji = "📈" if diff > 0 else "📉"
            message += f"{emoji} {name}\n   {old:.2f}€ → {new:.2f}€\n\n"
        
        if len(changes) > 5:
            message += f"_...y {len(changes) - 5} más_"
        
        await self._send_to_channels(
            NotificationType.PRICE_CHANGE,
            message,
            channels,
            {"changes_count": len(changes)}
        )
    
    async def notify_scraper_complete(
        self,
        supplier: str,
        products_count: int,
        duration_seconds: int = 0,
        channels: List[NotificationChannel] = None
    ):
        """Notify when a scraper completes"""
        channels = channels or [NotificationChannel.TELEGRAM]
        
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        
        message = f"""
✅ *Scraper Completado - {supplier}*

📦 Productos extraídos: *{products_count}*
⏱️ Duración: {minutes}m {seconds}s
🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        await self._send_to_channels(
            NotificationType.SCRAPER_COMPLETE,
            message,
            channels,
            {"supplier": supplier, "count": products_count}
        )
    
    async def notify_scraper_error(
        self,
        supplier: str,
        error: str,
        channels: List[NotificationChannel] = None
    ):
        """Notify when a scraper fails"""
        channels = channels or [NotificationChannel.TELEGRAM]
        
        message = f"""
❌ *Error en Scraper - {supplier}*

{error[:200]}

🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        await self._send_to_channels(
            NotificationType.SCRAPER_ERROR,
            message,
            channels,
            {"supplier": supplier, "error": error}
        )
    
    async def notify_report_ready(
        self,
        report_name: str,
        download_url: str = "",
        channels: List[NotificationChannel] = None
    ):
        """Notify when a report is ready"""
        channels = channels or [NotificationChannel.TELEGRAM]
        
        message = f"""
📊 *Reporte Generado*

📄 {report_name}
🔗 {download_url if download_url else 'Disponible en el dashboard'}

🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        await self._send_to_channels(
            NotificationType.REPORT_READY,
            message,
            channels,
            {"report": report_name}
        )
    
    # ========== INTERNAL ==========
    
    async def _send_to_channels(
        self,
        notification_type: NotificationType,
        message: str,
        channels: List[NotificationChannel],
        metadata: dict = None
    ):
        """Send notification to multiple channels"""
        results = {}
        
        for channel in channels:
            if channel == NotificationChannel.TELEGRAM:
                sent = await self.broadcast_telegram(message)
                results[channel.value] = sent
            # Add more channels here (WhatsApp, Email, etc.)
        
        # Log to history
        self.notification_history.append({
            "type": notification_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "channels": [c.value for c in channels],
            "results": results,
            "metadata": metadata
        })
        
        # Keep history limited
        if len(self.notification_history) > 100:
            self.notification_history = self.notification_history[-100:]
    
    def get_history(self, limit: int = 20) -> List[dict]:
        """Get notification history"""
        return self.notification_history[-limit:]
    
    def get_stats(self) -> dict:
        """Get notification statistics"""
        return {
            "total_subscribers": len(self.telegram_chat_ids),
            "telegram_configured": bool(self.telegram_token),
            "notifications_sent": len(self.notification_history),
            "last_notification": self.notification_history[-1] if self.notification_history else None
        }


# ========== GLOBAL INSTANCE ==========

notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    return notification_service
