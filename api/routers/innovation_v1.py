from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.ai.engine import SmartAgent
from core.scraping.thordata import ThorDataClient
from core.scraping.xpander import XpanderAgent

router = APIRouter(prefix="/innovation", tags=["Innovation Features"])

# --- Models ---
class ToTRequest(BaseModel):
    problem: str

class ScrapeRequest(BaseModel):
    url: str
    engine: str = "thordata" # thordata, xpander

# --- Endpoints ---

@router.post("/ai/solve")
async def solve_with_tot(req: ToTRequest):
    """
    Solves a problem using the Tree of Thought reasoning engine.
    """
    agent = SmartAgent()
    solution = await agent.solve(req.problem)
    return {"problem": req.problem, "solution": solution}

@router.post("/scraping/proxy")
def get_proxy(country: str = "es"):
    """
    Returns a ThorData residential proxy formatting string.
    """
    client = ThorDataClient()
    return {"proxy": client.get_residential_proxy(country)}

@router.post("/scraping/extract")
def extract_data(req: ScrapeRequest):
    """
    Extracts data using the selected advanced engine.
    """
    if req.engine == "thordata":
        client = ThorDataClient()
        result = client.scrape_url(req.url)
        return {"engine": "thordata", "content_snippet": result[:200] if result else None}
    
    elif req.engine == "xpander":
        agent = XpanderAgent()
        mission_id = agent.create_mission(f"Scrape {req.url}")
        results = agent.get_mission_results(mission_id)
        return {"engine": "xpander", "mission_id": mission_id, "results": results}
    
    else:
        raise HTTPException(status_code=400, detail="Unknown engine")
