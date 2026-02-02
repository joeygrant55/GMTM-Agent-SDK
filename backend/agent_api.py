"""
Agent API Endpoints
Routes for all SPARQ agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import os

# Add agents to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import both versions
from agents.camp_finder_standalone import CampFinderAgent  # Simple version
from agents.autonomous_camp_finder import autonomous_camp_finder  # Full Agent SDK version

router = APIRouter(prefix="/api", tags=["Agents"])

class CampSearchRequest(BaseModel):
    athlete_id: int
    max_results: int = 10

@router.post("/agent/find-camps")
async def find_camps(request: CampSearchRequest):
    """
    Find camps and combines for an athlete
    
    POST /api/agent/find-camps
    Body: {"athlete_id": 383, "max_results": 10}
    """
    try:
        agent = CampFinderAgent()
        result = agent.find_camps_for_athlete(
            athlete_id=request.athlete_id,
            max_results=request.max_results
        )
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/find-camps/{athlete_id}")
async def find_camps_get(athlete_id: int, max_results: int = 10, autonomous: bool = True):
    """
    Find camps (GET version for easy testing)
    
    GET /api/agent/find-camps/383?max_results=10&autonomous=true
    
    Parameters:
    - autonomous=true: Use full Agent SDK with web research (default)
    - autonomous=false: Use simple version (faster, no web access)
    """
    try:
        if autonomous:
            # Use full Agent SDK with Claude + web tools
            result = autonomous_camp_finder.find_camps(
                athlete_id=athlete_id,
                max_results=max_results
            )
        else:
            # Use simple version (no web access)
            agent = CampFinderAgent()
            result = agent.find_camps_for_athlete(
                athlete_id=athlete_id,
                max_results=max_results
            )
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
