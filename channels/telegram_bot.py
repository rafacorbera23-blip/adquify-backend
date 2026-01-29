"""
Adquify Telegram Bot
=====================
Bot de Telegram para búsqueda de productos en el catálogo Adquify.

Comandos:
- /start - Mensaje de bienvenida
- /buscar <texto> - Buscar productos por nombre
- /categoria <nombre> - Filtrar por categoría
- /stats - Estadísticas del catálogo
- Enviar imagen - Búsqueda visual automática

Configuración:
- TELEGRAM_BOT_TOKEN: Token del bot de BotFather
- ADQUIFY_API_URL: URL del API backend (default: http://localhost:8001)
"""

import os
import asyncio
import logging
from typing import Optional
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import httpx

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADQUIFY_API_URL = os.getenv("ADQUIFY_API_URL", "http://localhost:8001")


class AdquifyTelegramBot:
    """Bot de Telegram que conecta con el catálogo Adquify"""
    
    def __init__(self, token: Optional[str] = None, api_url: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.api_url = api_url or ADQUIFY_API_URL
        self.application = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        if not self.token:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set. Bot will not start.")
    
    async def _api_get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to Adquify API"""
        try:
            response = await self.http_client.get(
                f"{self.api_url}{endpoint}",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API Error: {e}")
            return {"error": str(e)}
    
    async def _api_post(self, endpoint: str, data: dict = None, files: dict = None) -> dict:
        """Make POST request to Adquify API"""
        try:
            if files:
                response = await self.http_client.post(
                    f"{self.api_url}{endpoint}",
                    files=files
                )
            else:
                response = await self.http_client.post(
                    f"{self.api_url}{endpoint}",
                    json=data
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API Error: {e}")
            return {"error": str(e)}
    
    # ========== COMMAND HANDLERS ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /start"""
        welcome_message = """
🏢 *¡Bienvenido a Adquify!*

Soy tu asistente para buscar productos en nuestro catálogo B2B.

📋 *Comandos disponibles:*
• /buscar `<texto>` - Buscar productos
• /categoria `<nombre>` - Filtrar por categoría
• /categorias - Ver categorías disponibles
• /stats - Ver estadísticas

📸 *Búsqueda visual:*
Envía una imagen y buscaré productos similares.

💬 O simplemente escríbeme lo que buscas.
        """
        await update.message.reply_text(
            welcome_message.strip(),
            parse_mode='Markdown'
        )
    
    async def cmd_buscar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /buscar <texto>"""
        if not context.args:
            await update.message.reply_text(
                "❓ Escribe qué producto buscas.\n"
                "Ejemplo: `/buscar sofá verde`",
                parse_mode='Markdown'
            )
            return
        
        query = " ".join(context.args)
        await self._search_and_reply(update, query)
    
    async def cmd_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /categoria <nombre>"""
        if not context.args:
            await update.message.reply_text(
                "❓ Escribe qué categoría quieres ver.\n"
                "Ejemplo: `/categoria Sofás`\n"
                "Usa /categorias para ver las disponibles.",
                parse_mode='Markdown'
            )
            return
        
        category = " ".join(context.args)
        await self._search_and_reply(update, None, category=category)
    
    async def cmd_categorias(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /categorias - lista categorías disponibles"""
        # Get products and extract unique categories
        products = await self._api_get("/products", {"limit": 500})
        
        if isinstance(products, list):
            categories = set(p.get("category", "Sin categoría") for p in products)
            categories = sorted([c for c in categories if c])
            
            if categories:
                cat_list = "\n".join([f"• {c}" for c in categories[:20]])
                await update.message.reply_text(
                    f"📁 *Categorías disponibles:*\n\n{cat_list}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("No hay categorías disponibles.")
        else:
            await update.message.reply_text("Error al obtener categorías.")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /stats"""
        stats = await self._api_get("/stats")
        
        if "error" not in stats:
            message = f"""
📊 *Estadísticas del Catálogo*

📦 Total productos: *{stats.get('total_products', 0)}*
🏭 Proveedores activos: *{stats.get('active_scrapers', 0)}*
✅ Publicados: *{stats.get('published_products', 0)}*
⏳ Pendientes: *{stats.get('pending_products', 0)}*
🖼️ Imágenes: *{stats.get('images_stored', 0)}*

🕐 Última sync: {stats.get('last_sync', 'N/A')}
            """
            await update.message.reply_text(message.strip(), parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error al obtener estadísticas.")
    
    # ========== MESSAGE HANDLERS ==========
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensajes de texto (búsqueda natural)"""
        text = update.message.text.strip()
        
        if len(text) < 2:
            return
        
        # Use the chat engine for natural language
        response = await self._api_post("/chat", {"message": text})
        
        if "error" not in response:
            await update.message.reply_text(
                response.get("response", "No encontré resultados."),
                parse_mode='Markdown'
            )
        else:
            # Fallback to simple search
            await self._search_and_reply(update, text)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para fotos (búsqueda visual)"""
        await update.message.reply_text("🔍 Buscando productos similares...")
        
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo
        photo_bytes = BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        
        # Send to visual search API
        files = {"file": ("image.jpg", photo_bytes, "image/jpeg")}
        results = await self._api_post("/search/image", files=files)
        
        if "error" not in results and results:
            await self._format_product_results(update, results[:5], "🖼️ Productos similares:")
        else:
            await update.message.reply_text(
                "😕 No encontré productos similares a esa imagen.\n"
                "Prueba con otra imagen o usa /buscar."
            )
    
    # ========== HELPERS ==========
    
    async def _search_and_reply(
        self,
        update: Update,
        query: Optional[str] = None,
        category: Optional[str] = None
    ):
        """Search products and send formatted reply"""
        params = {"limit": 10}
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        
        products = await self._api_get("/products", params)
        
        if isinstance(products, list) and products:
            title = f"🔍 Resultados para *{query}*:" if query else f"📁 Categoría *{category}*:"
            await self._format_product_results(update, products[:5], title)
        else:
            await update.message.reply_text(
                f"😕 No encontré productos{' para ' + query if query else ''}.\n"
                "Prueba con otros términos."
            )
    
    async def _format_product_results(
        self,
        update: Update,
        products: list,
        title: str
    ):
        """Format and send product results with inline buttons"""
        message = f"{title}\n\n"
        
        for i, product in enumerate(products, 1):
            name = product.get("name", "Sin nombre")[:50]
            price = product.get("price", 0)
            category = product.get("category", "")
            supplier = product.get("supplier", "")
            
            message += (
                f"*{i}. {name}*\n"
                f"   💰 {price:.2f}€ | 📁 {category}\n"
                f"   🏭 {supplier}\n\n"
            )
        
        message += f"_Mostrando {len(products)} resultados_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    # ========== BOT LIFECYCLE ==========
    
    def setup_handlers(self):
        """Configure all handlers"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("buscar", self.cmd_buscar))
        self.application.add_handler(CommandHandler("categoria", self.cmd_categoria))
        self.application.add_handler(CommandHandler("categorias", self.cmd_categorias))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        
        # Photo handler (visual search)
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Text handler (natural language)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_text
        ))
    
    async def start(self):
        """Start the bot"""
        if not self.token:
            logger.error("❌ Cannot start bot: TELEGRAM_BOT_TOKEN not set")
            return
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("🚀 Starting Adquify Telegram Bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    
    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        await self.http_client.aclose()
        logger.info("🛑 Bot stopped.")


# ========== CLI ENTRY POINT ==========

async def main():
    """Main entry point for running the bot standalone"""
    bot = AdquifyTelegramBot()
    
    try:
        await bot.start()
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
