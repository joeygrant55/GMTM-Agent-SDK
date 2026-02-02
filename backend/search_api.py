"""
Simplified SPARQ Search API
============================

Direct database search without Agent SDK dependency.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

# Add agents to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents'))
from db_connector import get_db

router = APIRouter(prefix="/api", tags=["Search"])

class AthleteResult(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    graduation_year: Optional[int]
    city: Optional[str]
    state: Optional[str]
    position: Optional[str]
    sport: Optional[str]
    metrics: Dict[str, Any] = {}
    profile_url: str
    avatar_url: Optional[str] = None
    event_name: Optional[str] = None
    sparq_score: Optional[int] = None

class SearchResponse(BaseModel):
    athletes: List[AthleteResult]
    total: int
    query_time_ms: int

@router.get("/search", response_model=SearchResponse)
async def search_athletes(
    state: Optional[str] = Query(None, description="State abbreviation (e.g. TX, FL, CA)"),
    position: Optional[str] = Query(None, description="Position name"),
    graduation_year: Optional[int] = Query(None, description="Graduation year"),
    sport: Optional[str] = Query(None, description="Sport name"),
    limit: int = Query(10, le=50, description="Max results")
):
    """
    Search for athletes with verified SPARQ metrics.
    
    Example: /api/search?state=TX&position=WR&graduation_year=2026&limit=10
    """
    start_time = datetime.now()
    
    # Build query
    query = """
        SELECT DISTINCT
            u.user_id,
            u.first_name,
            u.last_name,
            u.graduation_year,
            l.city,
            l.province as state,
            p.name as position,
            s.name as sport,
            u.avatar_uri,
            ipe.name as event_name,
            MAX(m.score) as sparq_score
        FROM users u
        LEFT JOIN locations l ON u.location_id = l.location_id
        LEFT JOIN career c ON u.user_id = c.user_id AND c.is_current = 1
        LEFT JOIN user_positions up ON c.career_id = up.career_id
        LEFT JOIN positions p ON up.position_id = p.position_id
        LEFT JOIN sports s ON c.sport_id = s.sport_id
        LEFT JOIN metrics m ON u.user_id = m.user_id AND m.verified = 1
        LEFT JOIN in_person_events ipe ON m.in_person_event_id = ipe.in_person_event_id
        WHERE u.type = 1 AND u.visibility = 2
    """
    
    params = []
    
    if state:
        query += " AND l.province = %s"
        params.append(state.upper())
    
    if position:
        query += " AND p.name LIKE %s"
        params.append(f"%{position}%")
    
    if graduation_year:
        query += " AND u.graduation_year = %s"
        params.append(graduation_year)
    
    if sport:
        query += " AND s.name LIKE %s"
        params.append(f"%{sport}%")
    
    query += " GROUP BY u.user_id"
    query += f" LIMIT {limit}"
    
    try:
        db = get_db()
        results = db.execute_query(query, tuple(params) if params else None)
        
        athletes = []
        for row in results:
            athletes.append(AthleteResult(
                user_id=row['user_id'],
                first_name=row['first_name'] or 'Unknown',
                last_name=row['last_name'] or '',
                graduation_year=row.get('graduation_year'),
                city=row.get('city') or '',
                state=row.get('state') or '',
                position=row.get('position'),
                sport=row.get('sport'),
                metrics={},
                profile_url=f"https://gmtm.com/profile/{row['user_id']}",
                avatar_url=row.get('avatar_uri'),
                event_name=row.get('event_name'),
                sparq_score=row.get('sparq_score')
            ))
        
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            athletes=athletes,
            total=len(athletes),
            query_time_ms=int(elapsed)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/athlete/{user_id}", response_model=AthleteResult)
async def get_athlete(user_id: int):
    """
    Get specific athlete by user_id.
    
    Example: /api/athlete/383
    """
    query = """
        SELECT DISTINCT
            u.user_id,
            u.first_name,
            u.last_name,
            u.graduation_year,
            l.city,
            l.province as state,
            p.name as position,
            s.name as sport,
            u.avatar_uri,
            ipe.name as event_name,
            MAX(m.score) as sparq_score
        FROM users u
        LEFT JOIN locations l ON u.location_id = l.location_id
        LEFT JOIN career c ON u.user_id = c.user_id AND c.is_current = 1
        LEFT JOIN user_positions up ON c.career_id = up.career_id
        LEFT JOIN positions p ON up.position_id = p.position_id
        LEFT JOIN sports s ON c.sport_id = s.sport_id
        LEFT JOIN metrics m ON u.user_id = m.user_id AND m.verified = 1
        LEFT JOIN in_person_events ipe ON m.in_person_event_id = ipe.in_person_event_id
        WHERE u.user_id = %s AND u.type = 1
        GROUP BY u.user_id
    """
    
    try:
        db = get_db()
        results = db.execute_query(query, (user_id,))
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Athlete {user_id} not found")
        
        row = results[0]
        return AthleteResult(
            user_id=row['user_id'],
            first_name=row['first_name'] or 'Unknown',
            last_name=row['last_name'] or '',
            graduation_year=row.get('graduation_year'),
            city=row.get('city') or '',
            state=row.get('state') or '',
            position=row.get('position'),
            sport=row.get('sport'),
            metrics={},
            profile_url=f"https://gmtm.com/profile/{row['user_id']}",
            avatar_url=row.get('avatar_uri'),
            event_name=row.get('event_name'),
            sparq_score=row.get('sparq_score')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch athlete: {str(e)}")

@router.get("/health")
async def health():
    """API health check"""
    return {
        "status": "healthy",
        "service": "SPARQ Search API",
        "timestamp": datetime.utcnow().isoformat()
    }
