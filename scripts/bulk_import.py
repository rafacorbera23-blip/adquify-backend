import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.agent_harvester import HarvesterAgent

# Configure Logging to file
log_dir = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "bulk_import.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("BulkImport")

async def main():
    logger.info("🐃 Starting BULK IMPORT Process")
    agent = HarvesterAgent()
    try:
        await agent.run_mission()
        logger.info("✅ Bulk Import Completed Successfully")
    except Exception as e:
        logger.error(f"❌ Bulk Import Failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Import Stopped by User")
