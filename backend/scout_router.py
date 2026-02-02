"""
Scout AI Router
===============

FastAPI router for Scout AI talent discovery endpoints.
Handles chat, athlete profiles, saved searches, and alerts.
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt

# Import agents
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.scout_agent import run_scout_search, run_scout_search_streaming
from agents.query_builder import QueryBuilder, build_search_query

# ============================================
# CONFIGURATION
# ============================================

router = APIRouter(prefix="/scout", tags=["Scout AI"])
security = HTTPBearer(auto_error=False)

# JWT Configuration (for MVP standalone auth)
JWT_SECRET = os.environ.get("SCOUT_JWT_SECRET", "scout-ai-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"

# ============================================
# DATA MODELS
# ============================================

class ChatMessage(BaseModel):
    """Incoming chat message from coach"""
    message: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")


class AthleteSearchResult(BaseModel):
    """Athlete in search results"""
    user_id: int
    first_name: str
    last_name: str
    graduation_year: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    position: Optional[str] = None
    sport: Optional[str] = None
    metrics: Dict[str, Any] = {}
    film_count: int = 0
    profile_url: str
    avatar_url: Optional[str] = None
    # SPARQ-specific fields
    event_name: Optional[str] = None
    sparq_score: Optional[int] = None
    percentile: Optional[int] = None


class ChatResponse(BaseModel):
    """Response from Scout AI"""
    response: str
    query: str
    conversation_id: Optional[str] = None
    athletes_found: int = 0
    athletes: List[AthleteSearchResult] = []
    timestamp: str


class AthleteResult(BaseModel):
    """Athlete search result"""
    user_id: int
    first_name: str
    last_name: str
    graduation_year: Optional[int]
    city: Optional[str]
    state: Optional[str]
    position: Optional[str]
    sport: Optional[str]
    metrics: Dict[str, Any] = {}
    film_count: int = 0
    profile_url: str
    avatar_url: Optional[str]


# ============================================
# FULL PROFILE DATA MODELS
# ============================================

class AthleteMetric(BaseModel):
    """Individual metric with SPARQ data"""
    name: str
    value: str
    sparq_score: Optional[int] = None
    percentile: Optional[int] = None
    event_name: Optional[str] = None


class FilmHighlight(BaseModel):
    """Video highlight from combine or user upload"""
    film_id: int
    title: str
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    published_on: Optional[str] = None


class SocialProfile(BaseModel):
    """Social media or recruiting profile link"""
    platform: str
    url: str


class FullAthleteProfile(BaseModel):
    """Comprehensive athlete profile with all available data"""
    user_id: int
    first_name: str
    last_name: str
    graduation_year: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    avatar_url: Optional[str] = None
    about: Optional[str] = None
    metrics: List[AthleteMetric] = []
    highlights: List[FilmHighlight] = []
    social_profiles: List[SocialProfile] = []
    gmtm_profile_url: str


# ============================================
# NFL COMPARISON DATA MODELS
# ============================================

class NFLMetricComparison(BaseModel):
    """Comparison result for a single metric"""
    metric_name: str
    athlete_value: float
    nfl_percentile: int
    better_than: List[str] = []  # "Player Name (value)"
    similar_to: List[str] = []
    worse_than: List[str] = []


class SPARQProfile(BaseModel):
    """NFL player with similar SPARQ profile"""
    name: str
    college: str
    position: str
    sparq_score: float
    draft_class: Optional[int] = None
    similarity: float


class SPARQComparison(BaseModel):
    """Historical SPARQ comparison data"""
    similar_profiles: List[SPARQProfile] = []
    sparq_percentile: Optional[int] = None
    estimated_sparq: Optional[float] = None
    sparq_headline: Optional[str] = None


class NFLComparisonResponse(BaseModel):
    """Complete NFL Combine comparison result"""
    position: str
    overall_percentile: int
    metrics: Dict[str, NFLMetricComparison]
    pro_comparison: str
    headline: str
    sparq_comparison: Optional[SPARQComparison] = None


class SearchRequest(BaseModel):
    """Structured search request (alternative to natural language)"""
    state: Optional[str] = None
    position: Optional[str] = None
    graduation_year: Optional[int] = None
    sport: Optional[str] = None
    min_40_time: Optional[float] = None
    max_40_time: Optional[float] = None
    min_vertical: Optional[float] = None
    min_bench: Optional[float] = None
    verified_only: bool = False
    limit: int = Field(default=10, le=50)


class SavedSearchCreate(BaseModel):
    """Request to save a search"""
    name: str = Field(..., min_length=1, max_length=100)
    query_text: str
    is_alert: bool = False
    alert_frequency: Optional[str] = Field(None, pattern="^(daily|weekly|instant)$")


class SavedSearchResponse(BaseModel):
    """Saved search details"""
    saved_search_id: int
    name: str
    query_text: str
    is_alert: bool
    alert_frequency: Optional[str]
    last_result_count: int
    created_on: str


class UserLogin(BaseModel):
    """Login request"""
    email: str
    password: str


class UserRegister(BaseModel):
    """Registration request"""
    email: str
    password: str
    first_name: str
    last_name: str
    organization: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours


# ============================================
# AUTHENTICATION
# ============================================

def create_token(user_id: int, email: str) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow().timestamp() + 86400  # 24 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, else None"""
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None


# ============================================
# AUTH ENDPOINTS (MVP Standalone)
# ============================================

# In-memory user store for MVP (replace with database in production)
_users_store: Dict[str, Dict[str, Any]] = {}
_user_id_counter = 1


@router.post("/auth/register", response_model=TokenResponse)
async def register(user: UserRegister):
    """
    Register a new coach account.
    MVP: In-memory storage. Production: Use GMTM OAuth or database.
    """
    global _user_id_counter

    if user.email in _users_store:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = _user_id_counter
    _user_id_counter += 1

    _users_store[user.email] = {
        "user_id": user_id,
        "email": user.email,
        "password": user.password,  # TODO: Hash in production!
        "first_name": user.first_name,
        "last_name": user.last_name,
        "organization": user.organization,
        "created_at": datetime.utcnow().isoformat()
    }

    token = create_token(user_id, user.email)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
async def login(user: UserLogin):
    """
    Login with email/password.
    MVP: In-memory storage. Production: Use GMTM OAuth or database.
    """
    stored_user = _users_store.get(user.email)
    if not stored_user or stored_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(stored_user["user_id"], user.email)
    return TokenResponse(access_token=token)


@router.get("/auth/me")
async def get_me(user: Dict = Depends(get_current_user)):
    """Get current user profile"""
    stored_user = None
    for email, data in _users_store.items():
        if data["user_id"] == user["user_id"]:
            stored_user = data
            break

    if not stored_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": stored_user["user_id"],
        "email": stored_user["email"],
        "first_name": stored_user["first_name"],
        "last_name": stored_user["last_name"],
        "organization": stored_user.get("organization")
    }


# ============================================
# CHAT ENDPOINTS
# ============================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Process a natural language search query.

    Examples:
    - "Show me top 5 running backs in Texas with sub-4.5 40"
    - "Find quarterbacks graduating 2026 in Florida"
    - "Athletes with over 36 inch vertical jump"
    """
    try:
        # Run Scout AI search
        result = await run_scout_search(
            natural_query=message.message,
            user_id=user["user_id"] if user else None,
            max_results=10
        )

        # Transform athletes to response model
        athletes = []
        for athlete_data in result.get("athletes", []):
            # Skip athletes with missing required data
            user_id = athlete_data.get("user_id")
            if not user_id:
                continue

            athletes.append(AthleteSearchResult(
                user_id=user_id,
                first_name=athlete_data.get("first_name") or "Unknown",
                last_name=athlete_data.get("last_name") or "",
                graduation_year=athlete_data.get("graduation_year"),
                city=athlete_data.get("city") or "",
                state=athlete_data.get("state") or "",
                position=athlete_data.get("position"),
                sport=athlete_data.get("sport"),
                metrics=athlete_data.get("metrics") or {},
                film_count=athlete_data.get("film_count", 0),
                profile_url=athlete_data.get("profile_url") or f"https://gmtm.com/profile/{user_id}",
                avatar_url=athlete_data.get("avatar_url"),
                # SPARQ fields
                event_name=athlete_data.get("event_name"),
                sparq_score=athlete_data.get("sparq_score"),
                percentile=athlete_data.get("percentile")
            ))

        return ChatResponse(
            response=result.get("response", "No response generated"),
            query=message.message,
            conversation_id=message.conversation_id,
            athletes_found=result.get("athletes_found", 0),
            athletes=athletes,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(
    message: ChatMessage,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Process a natural language search query with streaming events.
    Returns Server-Sent Events for real-time UI updates.

    Event types:
    - start: Search initiated
    - progress: Processing stage update
    - thinking: AI thinking/analyzing
    - tool_start: Database query starting
    - tool_complete: Database query finished
    - complete: Final results
    - error: Error occurred
    """
    async def event_generator():
        try:
            async for event in run_scout_search_streaming(
                natural_query=message.message,
                user_id=user["user_id"] if user else None,
                max_results=10
            ):
                # Format as SSE
                data = json.dumps(event)
                yield f"data: {data}\n\n"

                # If complete or error, add final done event
                if event.get("event") in ["complete", "error"]:
                    yield "data: [DONE]\n\n"
                    break

        except Exception as e:
            error_event = {
                "event": "error",
                "message": f"Stream error: {str(e)}",
                "stage": "error"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for streaming chat responses.

    Connect with: ws://host/scout/ws/chat?token=<jwt_token>
    Send: {"message": "your search query"}
    Receive: {"type": "chunk", "content": "..."} or {"type": "done", "response": "..."}
    """
    await websocket.accept()

    # Verify token if provided
    user = None
    if token:
        try:
            user = decode_token(token)
        except HTTPException:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                await websocket.send_json({"type": "error", "message": "No message provided"})
                continue

            # Send processing indicator
            await websocket.send_json({"type": "status", "message": "Searching..."})

            try:
                # Run search
                result = await run_scout_search(
                    natural_query=message,
                    user_id=user["user_id"] if user else None
                )

                # Send result
                await websocket.send_json({
                    "type": "done",
                    "response": result.get("response", ""),
                    "query": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Search failed: {str(e)}"
                })

    except WebSocketDisconnect:
        pass


# ============================================
# STRUCTURED SEARCH ENDPOINT
# ============================================

@router.post("/search")
async def structured_search(
    request: SearchRequest,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Execute a structured search with specific filters.
    Alternative to natural language chat for programmatic access.
    """
    # Build metric filters
    metric_filters = []
    if request.max_40_time:
        metric_filters.append(("40", "<", request.max_40_time))
    if request.min_vertical:
        metric_filters.append(("vertical", ">", request.min_vertical))
    if request.min_bench:
        metric_filters.append(("bench", ">", request.min_bench))

    # Build query
    query = build_search_query(
        state=request.state,
        position=request.position,
        graduation_year=request.graduation_year,
        sport=request.sport,
        metric_filters=metric_filters if metric_filters else None,
        limit=request.limit,
        verified_only=request.verified_only
    )

    # TODO: Execute query via GMTM MCP
    # For now, return the generated query for testing
    return {
        "status": "query_generated",
        "sql": query,
        "filters": request.dict(exclude_none=True),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# ATHLETE PROFILE ENDPOINTS
# ============================================

@router.get("/athletes/{user_id}")
async def get_athlete_profile(
    user_id: int,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Get basic athlete profile info.
    For full profile with metrics, highlights, social links use /athletes/{id}/full
    """
    return {
        "user_id": user_id,
        "profile_url": f"https://gmtm.com/athletes/{user_id}",
        "message": "Use /athletes/{id}/full for comprehensive profile",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/athletes/{user_id}/full", response_model=FullAthleteProfile)
async def get_full_athlete_profile(
    user_id: int,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Get comprehensive athlete profile with all available data.

    Returns:
    - Basic info (name, location, graduation year, avatar, bio)
    - All SPARQ metrics with scores and percentiles
    - Video highlights with thumbnails
    - Social media profile links
    - Correct GMTM profile URL
    """
    try:
        from agents.profile_fetcher import fetch_full_profile
        profile_data = await fetch_full_profile(user_id)
        return profile_data
    except ImportError:
        # Fallback if profile_fetcher not available - return minimal data
        first_name = "Athlete"
        last_name = str(user_id)
        slug = f"{first_name.lower()}-{last_name.lower()}"

        return FullAthleteProfile(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            gmtm_profile_url=f"https://gmtm.com/athletes/{user_id}/{slug}/feed",
            metrics=[],
            highlights=[],
            social_profiles=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.get("/athletes/{user_id}/nfl-comparison", response_model=NFLComparisonResponse)
async def get_nfl_comparison(
    user_id: int,
    position: str = Query(default="WR", description="Position for comparison (WR, RB, QB, CB, etc.)"),
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Compare athlete's SPARQ metrics to NFL Combine prospects.

    Returns:
    - Percentile rankings vs NFL prospects by position
    - Notable player comparisons (faster than X, similar to Y)
    - Pro comparison narrative
    - Shareable headline

    Example response:
    "Your 4.63s 40-yard dash is faster than 73% of NFL WR prospects,
    including Keenan Allen (4.71s)"
    """
    try:
        # First get the athlete's metrics from their profile
        from agents.profile_fetcher import fetch_full_profile
        profile_data = await fetch_full_profile(user_id)

        # Extract metrics into the format needed for comparison
        athlete_metrics = {}
        for metric in profile_data.get("metrics", []):
            name = metric.get("name", "").lower()
            value = metric.get("value", "")

            # Parse value to float
            try:
                numeric_value = float(str(value).replace('"', '').replace("'", '').strip())
            except (ValueError, TypeError):
                continue

            # Map metric names
            if "40" in name or "forty" in name:
                athlete_metrics["forty"] = numeric_value
            elif "vertical" in name:
                athlete_metrics["vertical"] = numeric_value
            elif "broad" in name:
                athlete_metrics["broad"] = numeric_value
            elif "shuttle" in name or "5-10-5" in name:
                athlete_metrics["shuttle"] = numeric_value
            elif "3-cone" in name or "three" in name:
                athlete_metrics["three_cone"] = numeric_value

        if not athlete_metrics:
            raise HTTPException(
                status_code=400,
                detail="No comparable metrics found for this athlete"
            )

        # Run NFL comparison
        from agents.nfl_benchmark_agent import compare_to_nfl
        result = compare_to_nfl(athlete_metrics, position)

        # Transform to response model
        metrics_response = {}
        for key, data in result.get("metrics", {}).items():
            metrics_response[key] = NFLMetricComparison(
                metric_name=data["metric_name"],
                athlete_value=data["athlete_value"],
                nfl_percentile=data["nfl_percentile"],
                better_than=data.get("better_than", []),
                similar_to=data.get("similar_to", []),
                worse_than=data.get("worse_than", [])
            )

        return NFLComparisonResponse(
            position=result["position"],
            overall_percentile=result["overall_percentile"],
            metrics=metrics_response,
            pro_comparison=result["pro_comparison"],
            headline=result["headline"]
        )

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Agent not available: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NFL comparison failed: {str(e)}")


# ============================================
# SAVED SEARCHES ENDPOINTS
# ============================================

# In-memory saved searches store for MVP
_saved_searches: Dict[int, List[Dict]] = {}
_search_id_counter = 1


@router.post("/searches/save", response_model=SavedSearchResponse)
async def save_search(
    search: SavedSearchCreate,
    user: Dict = Depends(get_current_user)
):
    """Save a search for later or as an alert"""
    global _search_id_counter

    user_id = user["user_id"]
    if user_id not in _saved_searches:
        _saved_searches[user_id] = []

    saved = {
        "saved_search_id": _search_id_counter,
        "name": search.name,
        "query_text": search.query_text,
        "is_alert": search.is_alert,
        "alert_frequency": search.alert_frequency,
        "last_result_count": 0,
        "created_on": datetime.utcnow().isoformat()
    }

    _saved_searches[user_id].append(saved)
    _search_id_counter += 1

    return SavedSearchResponse(**saved)


@router.get("/searches", response_model=List[SavedSearchResponse])
async def get_saved_searches(
    user: Dict = Depends(get_current_user)
):
    """List all saved searches for current user"""
    user_id = user["user_id"]
    searches = _saved_searches.get(user_id, [])
    return [SavedSearchResponse(**s) for s in searches]


@router.delete("/searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    user: Dict = Depends(get_current_user)
):
    """Delete a saved search"""
    user_id = user["user_id"]
    searches = _saved_searches.get(user_id, [])

    for i, s in enumerate(searches):
        if s["saved_search_id"] == search_id:
            del searches[i]
            return {"status": "deleted", "search_id": search_id}

    raise HTTPException(status_code=404, detail="Search not found")


@router.post("/searches/{search_id}/run")
async def run_saved_search(
    search_id: int,
    user: Dict = Depends(get_current_user)
):
    """Re-run a saved search"""
    user_id = user["user_id"]
    searches = _saved_searches.get(user_id, [])

    for s in searches:
        if s["saved_search_id"] == search_id:
            # Run the saved query
            result = await run_scout_search(
                natural_query=s["query_text"],
                user_id=user_id
            )
            return {
                "search": s,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

    raise HTTPException(status_code=404, detail="Search not found")


# ============================================
# ALERTS ENDPOINTS
# ============================================

@router.get("/alerts")
async def get_alerts(
    user: Dict = Depends(get_current_user)
):
    """Get all active alerts for current user"""
    user_id = user["user_id"]
    searches = _saved_searches.get(user_id, [])
    alerts = [s for s in searches if s.get("is_alert")]
    return [SavedSearchResponse(**a) for a in alerts]


@router.post("/alerts/{search_id}/toggle")
async def toggle_alert(
    search_id: int,
    user: Dict = Depends(get_current_user)
):
    """Toggle alert status on a saved search"""
    user_id = user["user_id"]
    searches = _saved_searches.get(user_id, [])

    for s in searches:
        if s["saved_search_id"] == search_id:
            s["is_alert"] = not s["is_alert"]
            return {
                "search_id": search_id,
                "is_alert": s["is_alert"],
                "message": "Alert enabled" if s["is_alert"] else "Alert disabled"
            }

    raise HTTPException(status_code=404, detail="Search not found")


# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def health():
    """Scout AI health check"""
    return {
        "status": "healthy",
        "service": "Scout AI",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
