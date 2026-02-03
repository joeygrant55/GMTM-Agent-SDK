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

# Import agents
from agents.camp_finder_standalone import CampFinderAgent  # Simple version
from agents.autonomous_camp_finder import autonomous_camp_finder  # Full Agent SDK version
from agents.orchestrator_agent import orchestrator  # Unified chat agent

router = APIRouter(prefix="/api", tags=["Agents"])

class CampSearchRequest(BaseModel):
    athlete_id: int
    max_results: int = 10

from typing import Optional
from fastapi.responses import StreamingResponse

class ChatRequest(BaseModel):
    athlete_id: int
    message: str
    conversation_history: list = []
    conversation_id: Optional[int] = None  # Optional - for persistent conversations

class ConversationCreate(BaseModel):
    user_id: int
    title: str = "New Chat"

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

def _get_agent_db():
    """Connect to Railway MySQL for agent conversations (separate from gmtm DB)"""
    import pymysql
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    load_dotenv()
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor
    )

import json as _json

# ── Conversation endpoints ──────────────────────────────

@router.get("/conversations/{user_id}")
async def list_conversations(user_id: int):
    """List all conversations for an athlete"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("""
                SELECT ac.id, ac.title, ac.created_at, ac.updated_at,
                       (SELECT COUNT(*) FROM agent_messages WHERE conversation_id = ac.id) as message_count
                FROM agent_conversations ac
                WHERE ac.user_id = %s
                ORDER BY ac.updated_at DESC
            """, (user_id,))
            convos = c.fetchall()
            for co in convos:
                co['created_at'] = str(co['created_at'])
                co['updated_at'] = str(co['updated_at'])
            return {"conversations": convos}
    finally:
        db.close()

@router.post("/conversations")
async def create_conversation(request: ConversationCreate):
    """Create a new conversation"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO agent_conversations (user_id, title) VALUES (%s, %s)",
                (request.user_id, request.title)
            )
            db.commit()
            conv_id = c.lastrowid
            return {"id": conv_id, "title": request.title}
    finally:
        db.close()

@router.get("/conversations/{user_id}/{conversation_id}")
async def get_conversation(user_id: int, conversation_id: int):
    """Get all messages in a conversation"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, title, created_at FROM agent_conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id)
            )
            conv = c.fetchone()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conv['created_at'] = str(conv['created_at'])
            
            c.execute(
                "SELECT id, role, content, tools_used, agent_steps, created_at FROM agent_messages WHERE conversation_id = %s ORDER BY created_at",
                (conversation_id,)
            )
            messages = c.fetchall()
            for m in messages:
                m['created_at'] = str(m['created_at'])
            return {"conversation": conv, "messages": messages}
    finally:
        db.close()

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete a conversation"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM agent_conversations WHERE id = %s", (conversation_id,))
            db.commit()
            return {"deleted": True}
    finally:
        db.close()

# ── Chat endpoint (with persistence) ────────────────────

@router.post("/agent/chat")
async def agent_chat(request: ChatRequest):
    """
    Unified chat interface with orchestrator agent.
    If conversation_id is provided, saves messages and loads history.
    """
    try:
        db = None
        conversation_id = request.conversation_id
        conversation_history = request.conversation_history
        
        # If conversation_id, load history from DB
        if conversation_id:
            db = _get_agent_db()
            with db.cursor() as c:
                c.execute(
                    "SELECT role, content FROM agent_messages WHERE conversation_id = %s ORDER BY created_at",
                    (conversation_id,)
                )
                db_messages = c.fetchall()
                if db_messages:
                    conversation_history = [{"role": m["role"], "content": m["content"]} for m in db_messages]
        
        # If no conversation_id, auto-create one
        if not conversation_id:
            db = db or _get_agent_db()
            with db.cursor() as c:
                # Auto-title from first message
                title = request.message[:60] + ("..." if len(request.message) > 60 else "")
                c.execute(
                    "INSERT INTO agent_conversations (user_id, title) VALUES (%s, %s)",
                    (request.athlete_id, title)
                )
                db.commit()
                conversation_id = c.lastrowid
        
        # Run the agent
        result = orchestrator.chat(
            athlete_id=request.athlete_id,
            message=request.message,
            conversation_history=conversation_history
        )
        
        # Save both messages to DB
        if db:
            with db.cursor() as c:
                # Save user message
                c.execute(
                    "INSERT INTO agent_messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
                    (conversation_id, request.message)
                )
                # Save assistant response
                c.execute(
                    "INSERT INTO agent_messages (conversation_id, role, content, tools_used, agent_steps) VALUES (%s, 'assistant', %s, %s, %s)",
                    (conversation_id, result.get('response', ''),
                     _json.dumps(result.get('tools_used', [])),
                     _json.dumps(result.get('agent_steps', [])))
                )
                db.commit()
            db.close()
        
        # Include conversation_id in response
        result['conversation_id'] = conversation_id
        return result
    
    except Exception as e:
        if db:
            db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/chat/stream")
async def agent_chat_stream(request: ChatRequest):
    """SSE streaming chat - shows tool use and text in real-time"""
    
    async def event_generator():
        conversation_id = request.conversation_id
        conversation_history = request.conversation_history
        
        # Load history from DB if conversation exists
        if conversation_id:
            try:
                db = _get_agent_db()
                with db.cursor() as c:
                    c.execute(
                        "SELECT role, content FROM agent_messages WHERE conversation_id = %s ORDER BY created_at",
                        (conversation_id,)
                    )
                    db_messages = c.fetchall()
                    if db_messages:
                        conversation_history = [{"role": m["role"], "content": m["content"]} for m in db_messages]
                db.close()
            except:
                pass
        
        # Auto-create conversation
        if not conversation_id:
            try:
                db = _get_agent_db()
                with db.cursor() as c:
                    title = request.message[:60] + ("..." if len(request.message) > 60 else "")
                    c.execute(
                        "INSERT INTO agent_conversations (user_id, title) VALUES (%s, %s)",
                        (request.athlete_id, title)
                    )
                    db.commit()
                    conversation_id = c.lastrowid
                db.close()
            except:
                pass
        
        # Send conversation_id first
        yield f"event: conversation_id\ndata: {conversation_id}\n\n"
        
        full_response = ""
        tools_used = []
        agent_steps = []
        
        for event in orchestrator.chat_stream(
            athlete_id=request.athlete_id,
            message=request.message,
            conversation_history=conversation_history
        ):
            evt = event.get("event", "status")
            data = event.get("data", "")
            
            if evt == "text":
                full_response += data.replace("\\n", "\n")
            elif evt == "done":
                try:
                    done_data = _json.loads(data)
                    tools_used = done_data.get("tools_used", [])
                    agent_steps = done_data.get("agent_steps", [])
                    # full_response already built from text events
                except:
                    pass
            
            # SSE data can't contain raw newlines - escape them
            safe_data = data.replace("\n", "\\n") if evt == "text" else data
            yield f"event: {evt}\ndata: {safe_data}\n\n"
        
        # Save messages to DB
        if conversation_id:
            try:
                db = _get_agent_db()
                with db.cursor() as c:
                    c.execute(
                        "INSERT INTO agent_messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
                        (conversation_id, request.message)
                    )
                    c.execute(
                        "INSERT INTO agent_messages (conversation_id, role, content, tools_used, agent_steps) VALUES (%s, 'assistant', %s, %s, %s)",
                        (conversation_id, full_response,
                         _json.dumps(tools_used), _json.dumps(agent_steps))
                    )
                    
                    # Auto-save as report if it was deep research (3+ tools used)
                    if len(tools_used) >= 3 and len(full_response) > 500:
                        # Detect report type
                        msg_lower = request.message.lower()
                        if any(w in msg_lower for w in ['college', 'program', 'school', 'university', 'fit']):
                            report_type = 'college_fit'
                        elif any(w in msg_lower for w in ['profile', 'metric', 'stats', 'compare', 'analysis']):
                            report_type = 'profile_analysis'
                        elif any(w in msg_lower for w in ['camp', 'combine', 'showcase']):
                            report_type = 'camp_research'
                        else:
                            report_type = 'research'
                        
                        title = request.message[:80] + ("..." if len(request.message) > 80 else "")
                        summary = full_response[:200] + "..."
                        
                        c.execute("""
                            INSERT INTO agent_reports (user_id, conversation_id, report_type, title, content, summary, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            request.athlete_id, conversation_id, report_type, title,
                            full_response, summary,
                            _json.dumps({"tools_used": tools_used, "agent_steps": agent_steps})
                        ))
                        
                        report_id = c.lastrowid
                        # Send report saved event
                        yield f"event: report_saved\ndata: {_json.dumps({'report_id': report_id, 'report_type': report_type, 'title': title})}\n\n"
                    
                    db.commit()
                db.close()
            except Exception as e:
                print(f"DB save error: {e}")
                pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
