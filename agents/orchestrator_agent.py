"""
Orchestrator Agent - Unified chat interface with all tools
Like Claude Code - one agent, many tools, conversational
"""

import os
import sys
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import pymysql

# Load environment
# Load env from multiple possible locations
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
load_dotenv()  # Also load from current dir or environment

# Add tools to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.web_tools import web_tools
from tools.recruiting_tools import recruiting_tools

# Anthropic for Claude
from anthropic import Anthropic

class OrchestratorAgent:
    """
    Master agent that orchestrates all recruiting tools
    Decides which tools to use based on athlete's question
    """
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.web_tools = web_tools
        self.recruiting_tools = recruiting_tools
        self.db = None
        
    def connect_db(self):
        """Connect to GMTM database"""
        if not self.db:
            self.db = pymysql.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database='gmtm',
                port=3306,
                cursorclass=pymysql.cursors.DictCursor
            )
    
    def close_db(self):
        """Close database connection"""
        if self.db:
            self.db.close()
            self.db = None
    
    def chat(self, athlete_id: int, message: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Main chat interface - agent decides what to do
        """
        try:
            self.connect_db()
            
            # Get athlete profile
            athlete = self._get_athlete_profile(athlete_id)
            if not athlete:
                return {"response": "I couldn't find your athlete profile. Please check your athlete ID."}
            
            print(f"\n💬 Athlete {athlete['first_name']} asks: {message}")
            
            # Define all available tools (Anthropic format)
            tools = [
                {
                    "name": "find_camps",
                    "description": "Search for football camps, combines, and showcases. Use when athlete asks about camps, training events, or testing opportunities.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City or state to search (e.g., 'Texas', 'Houston')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of camps to find",
                                "default": 5
                            }
                        },
                        "required": ["location"]
                    }
                },
                {
                    "name": "search_web",
                    "description": "Search the web for general recruiting information, news, or resources.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_athlete_stats",
                    "description": "Get athlete's metrics, SPARQ scores, and profile information from database.",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "draft_email",
                    "description": "Draft a personalized email to a coach or recruiter.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "recipient": {
                                "type": "string",
                                "description": "Who the email is to (e.g., 'Coach at University of Houston')"
                            },
                            "purpose": {
                                "type": "string",
                                "description": "Purpose of email (e.g., 'introduction', 'camp follow-up')"
                            }
                        },
                        "required": ["recipient", "purpose"]
                    }
                },
                {
                    "name": "match_programs",
                    "description": "Find college programs that match the athlete's profile. Searches by sport, position, and location. Shows which programs actively recruit athletes at this position based on scholarship offer history.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "State to filter programs (e.g., 'Texas', 'California'). Optional - leave empty for nationwide."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max programs to return",
                                "default": 15
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "analyze_profile",
                    "description": "Analyze the athlete's metrics compared to position averages. Shows percentile rankings, strengths, weaknesses, and areas to improve. Use when athlete asks about their recruiting profile, where they stand, or how to improve.",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "get_recruiting_calendar",
                    "description": "Get NCAA recruiting calendar info: contact periods, dead periods, evaluation periods, signing days, and key deadlines. Personalized to the athlete's graduation year and sport.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "sport": {
                                "type": "string",
                                "description": "Sport (e.g., 'football', 'basketball'). Defaults to athlete's sport."
                            },
                            "grad_year": {
                                "type": "integer",
                                "description": "Graduation year. Defaults to athlete's grad year."
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "get_film_guidance",
                    "description": "Get position-specific film and highlight reel guidance. What coaches look for, best platforms (Hudl, etc.), how to structure highlights, and tips for getting noticed.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "position": {
                                "type": "string",
                                "description": "Position for specific guidance. Defaults to athlete's position."
                            }
                        },
                        "required": []
                    }
                }
            ]
            
            # Build system prompt with athlete context
            system_prompt = f"""You are a SPARQ Agent - an AI recruiting coordinator helping athletes get recruited.

Athlete Profile:
- Name: {athlete['first_name']} {athlete['last_name']}
- Position: {athlete.get('position', 'N/A')}
- Location: {athlete.get('city', 'Unknown')}, {athlete.get('state', 'Unknown')}
- Sport: {athlete.get('sport', 'Football')}
- Grad Year: {athlete.get('graduation_year', 'N/A')}

Your Role:
You are an expert college recruiting advisor — think of yourself as a combination of a top recruiting analyst, a college counselor, and a player's agent. You know:
- Which programs are rising vs declining
- Coaching styles and what each program values
- Conference dynamics (SEC speed, Big Ten physicality, etc.)
- The difference between getting an offer and getting playing time
- How to evaluate fit beyond just athletics (academics, culture, location, depth charts)
- NCAA rules, eligibility, transfer portal dynamics

Your job is to give athletes advice they'd normally need to pay a recruiting service thousands of dollars for — but better, because you have real data.

IMPORTANT DATA QUALITY NOTE:
- Athlete metrics are mostly SELF-REPORTED (only 3% verified). Always note this.
- When comparing metrics, say "based on self-reported data across our athlete database"
- Star ratings from 247Sports/Rivals are from external sources and more reliable
- Scholarship offer data comes from athlete profiles and may not be complete

Communication Style:
- Professional but warm — like a trusted advisor, not a robot
- Use clear formatting: headers, bullet points, and PROPERLY FORMATTED markdown tables
- For tables: Always use proper markdown table syntax with | separators and --- header row
- Be specific: Don't say "some good programs" — name them, explain WHY they fit
- Be honest about fit levels: "reach", "target", "safety" like college admissions
- Include actionable next steps the athlete can take TODAY

When discussing college programs, always consider:
1. ATHLETIC FIT: Do the athlete's metrics match what the program recruits?
2. ACADEMIC FIT: Program academic reputation and requirements
3. PLAYING TIME: Current depth chart, upcoming departures, position needs
4. CULTURE FIT: Coaching style, program identity, conference style of play
5. GEOGRAPHIC FIT: Distance from home, region preferences
6. DEVELOPMENT: Strength program, position coaching reputation, NFL pipeline

Available Tools:
- find_camps: Find training camps and combines
- search_web: Research ANY recruiting info — use this to look up specific programs, coaches, depth charts, recruiting news, conference standings, transfer portal news
- get_athlete_stats: Get athlete's metrics from our database
- draft_email: Write personalized emails to coaches
- match_programs: Find college programs from our database (scholarship offer patterns)
- analyze_profile: Compare athlete's metrics to position averages with percentile rankings
- get_recruiting_calendar: NCAA recruiting dates and deadlines
- get_film_guidance: Position-specific highlight reel tips

STRATEGY: Go DEEP. You have up to 10 research iterations — use them. Don't give surface-level answers.

For college matching questions:
1. First: match_programs for database results + analyze_profile for the athlete's strengths
2. Then: For the top 3-5 best-fit programs, research EACH ONE individually using search_web:
   - Head coach and position coach names, background, coaching philosophy
   - Recent recruiting classes — who did they sign at this position?
   - Current depth chart — are there openings? Who's graduating/transferring?
   - Program culture — what's their identity? (e.g., "DBU" for LSU corners)
   - Academic strengths — what majors is the school known for?
   - Player development track record — do players improve? NFL draft picks at this position?
   - NIL landscape — what's the NIL situation at this school?
3. Finally: Synthesize everything into a comprehensive report with clear recommendations

For academic questions:
- Research what the athlete is interested in studying
- How does their high school curriculum prepare them?
- What are the academic requirements for each program?
- What support systems exist (tutoring, study hall, academic advisors)?
- Graduation rates for athletes at that school

For coaching staff questions:
- Coach's background and career path
- Coaching tree — who did they learn from?
- Player development reputation
- Previous recruits at this position — how did they develop?
- Coaching style and scheme fit for the athlete

Think like a $5,000/year recruiting service advisor. The athlete's family is counting on this information to make one of the biggest decisions of their life. Be thorough, specific, and honest.

Always use multiple tools when it makes the answer better. Don't just return raw data — interpret it, compare options, and give specific, actionable advice with clear reasoning."""

            # Build messages
            messages = []
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    if msg.get('role') in ['user', 'assistant']:
                        messages.append({
                            "role": msg['role'],
                            "content": msg.get('content', '')
                        })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Call agent with multi-turn tool use support
            print("🤖 Agent thinking...")
            
            tools_used = []
            agent_steps = []  # Track what agent is doing for UI
            all_tool_results = []  # Store all tool execution results
            max_iterations = 10  # Go deep - research coaching staffs, academics, player development
            
            for iteration in range(max_iterations):
                response = self.anthropic.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=8192,
                    system=system_prompt,
                    tools=tools,
                    messages=messages
                )
                
                print(f"   Iteration {iteration + 1}: {response.stop_reason}")
                
                if response.stop_reason != "tool_use":
                    # Agent finished - no more tools needed
                    break
                
                # Execute tools if agent wants them
                tool_results = []
                
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tools_used.append(tool_name)
                        
                        # Add step for UI visibility
                        step_description = self._get_step_description(tool_name, tool_input)
                        agent_steps.append(step_description)
                        print(f"   🔧 {step_description}")
                        
                        # Execute tool
                        result = self._execute_tool(tool_name, tool_input, athlete)
                        all_tool_results.append(result)  # Store for camp card extraction
                        
                        # Add result step
                        if result.get("success"):
                            if tool_name == "find_camps":
                                agent_steps.append(f"✅ Found {result.get('camps_found', 0)} camps")
                            else:
                                agent_steps.append(f"✅ {tool_name} complete")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(result)
                        })
                
                # Add tool results to conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                
                # Continue loop - agent may want to use more tools
            
            # After loop, extract final response
            response_text = ""
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    response_text = content_block.text
                    break
            
            # Extract structured data if agent found camps
            structured_data = None
            if 'find_camps' in tools_used:
                # Use REAL URLs from tool results
                structured_data = self._extract_camp_cards(response_text, all_tool_results)
            
            return {
                "response": response_text or "I've completed my research. How else can I help?",
                "tools_used": tools_used,
                "structured": structured_data,
                "agent_steps": agent_steps  # Show what agent did
            }
        
        except Exception as e:
            import traceback
            print(f"❌ Error: {e}")
            traceback.print_exc()
            return {
                "response": f"I encountered an error: {str(e)}. Please try asking differently or contact support.",
                "error": str(e)
            }
        finally:
            self.close_db()

    def chat_stream(self, athlete_id: int, message: str, conversation_history: list = None):
        """Streaming version - yields SSE events for real-time UI updates.
        Tool use phase: yields tool_start/tool_done events
        Text phase: yields text chunks as they stream from Claude
        """
        import copy
        try:
            self.connect_db()
            athlete = self._get_athlete_profile(athlete_id)
            if not athlete:
                yield {"event": "error", "data": "Athlete not found"}
                return

            # Build system prompt (same as chat method)
            system_prompt = f"""You are a SPARQ Agent - an AI recruiting coordinator helping athletes get recruited.

Athlete Profile:
- Name: {athlete['first_name']} {athlete['last_name']}
- Position: {athlete.get('position', 'N/A')}
- Location: {athlete.get('city', 'Unknown')}, {athlete.get('state', 'Unknown')}
- Sport: {athlete.get('sport', 'Football')}
- Grad Year: {athlete.get('graduation_year', 'N/A')}

Your Role:
You are an expert college recruiting advisor — think of yourself as a combination of a top recruiting analyst, a college counselor, and a player's agent. Go DEEP with research.

IMPORTANT: Athlete metrics are mostly SELF-REPORTED (only 3% verified). Always note this.

Think like a $5,000/year recruiting service advisor. Be thorough, specific, and honest.
Always use multiple tools when it makes the answer better."""

            tools = self._get_tool_definitions()

            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:
                    if msg.get('role') in ['user', 'assistant']:
                        messages.append({"role": msg['role'], "content": msg.get('content', '')})
            messages.append({"role": "user", "content": message})

            tools_used = []
            agent_steps = []
            max_iterations = 10

            yield {"event": "status", "data": "Starting research..."}

            for iteration in range(max_iterations):
                response = self.anthropic.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=8192,
                    system=system_prompt,
                    tools=tools,
                    messages=messages
                )

                if response.stop_reason != "tool_use":
                    # Final response - stream it
                    break

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tools_used.append(tool_name)

                        step = self._get_step_description(tool_name, tool_input)
                        agent_steps.append(step)
                        yield {"event": "tool_start", "data": json.dumps({"tool": tool_name, "step": step})}

                        result = self._execute_tool(tool_name, tool_input, athlete)

                        done_step = f"✅ {tool_name} complete"
                        agent_steps.append(done_step)
                        yield {"event": "tool_done", "data": json.dumps({"tool": tool_name, "step": done_step})}

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            # Stream the final text response
            yield {"event": "status", "data": "Writing report..."}

            # Re-run with streaming for the final text
            with self.anthropic.messages.stream(
                model="claude-opus-4-6",
                max_tokens=8192,
                system=system_prompt,
                messages=messages
            ) as stream:
                full_text = ""
                for text in stream.text_stream:
                    full_text += text
                    yield {"event": "text", "data": text}

            yield {"event": "done", "data": json.dumps({
                "tools_used": tools_used,
                "agent_steps": agent_steps,
                "full_response": full_text
            })}

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": str(e)}
        finally:
            self.close_db()

    def _get_tool_definitions(self):
        """Return tool definitions array (shared between chat and chat_stream)"""
        return [
            {
                "name": "find_camps",
                "description": "Search for football camps, combines, and showcases.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City/state to search near"},
                        "sport": {"type": "string", "description": "Sport type"},
                        "max_results": {"type": "integer", "description": "Max results", "default": 5}
                    }
                }
            },
            {
                "name": "search_web",
                "description": "Search the web for recruiting information, coaching staffs, program details, depth charts, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Max results", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_athlete_stats",
                "description": "Get the athlete's metrics and stats from the database.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "draft_email",
                "description": "Draft a personalized email to a college coach.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "coach_name": {"type": "string"},
                        "school": {"type": "string"},
                        "email_type": {"type": "string", "enum": ["introduction", "camp_followup", "interest", "visit_request"]}
                    },
                    "required": ["school", "email_type"]
                }
            },
            {
                "name": "match_programs",
                "description": "Find college programs matching athlete's profile from scholarship offer data.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "Filter by state"},
                        "limit": {"type": "integer", "default": 15}
                    }
                }
            },
            {
                "name": "analyze_profile",
                "description": "Compare athlete's metrics to position averages with percentile rankings.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_recruiting_calendar",
                "description": "Get NCAA recruiting calendar dates and deadlines.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sport": {"type": "string"},
                        "grad_year": {"type": "integer"}
                    }
                }
            },
            {
                "name": "get_film_guidance",
                "description": "Get position-specific highlight reel and film tips.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "position": {"type": "string"}
                    }
                }
            }
        ]
    
    def _get_athlete_profile(self, athlete_id: int) -> Optional[Dict]:
        """Get athlete from database"""
        with self.db.cursor() as cursor:
            query = """
            SELECT 
                u.user_id,
                u.first_name,
                u.last_name,
                u.graduation_year,
                l.city,
                l.province as state,
                p.name as position,
                s.name as sport
            FROM users u
            LEFT JOIN locations l ON u.location_id = l.location_id
            LEFT JOIN career c ON u.user_id = c.user_id AND c.is_current = 1
            LEFT JOIN user_positions up ON c.career_id = up.career_id
            LEFT JOIN positions p ON up.position_id = p.position_id
            LEFT JOIN sports s ON c.sport_id = s.sport_id
            WHERE u.user_id = %s
            LIMIT 1
            """
            cursor.execute(query, (athlete_id,))
            return cursor.fetchone()
    
    def _execute_tool(self, tool_name: str, tool_input: Dict, athlete: Dict) -> Dict:
        """Execute a tool and return results"""
        try:
            if tool_name == "find_camps":
                location = tool_input.get("location", athlete.get('state', 'Texas'))
                max_results = tool_input.get("max_results", 10)
                
                # Use web tools to search - get actual URLs
                query = f"{athlete.get('sport', 'football')} camps {location} 2026 registration"
                results = self.web_tools.search_web(query, max_results=max_results)
                
                # Format results with REAL URLs from search
                formatted_camps = []
                for result in results[:max_results]:
                    formatted_camps.append({
                        "name": result.get("title", "Camp"),
                        "url": result.get("url", ""),
                        "description": result.get("description", "")
                    })
                
                return {
                    "success": True,
                    "camps_found": len(formatted_camps),
                    "camps": formatted_camps
                }
            
            elif tool_name == "search_web":
                query = tool_input["query"]
                results = self.web_tools.search_web(query, max_results=10)
                return {
                    "success": True,
                    "results": results
                }
            
            elif tool_name == "get_athlete_stats":
                # Get metrics from database
                with self.db.cursor() as cursor:
                    query = """
                    SELECT m.title, m.value, m.score, m.percentile
                    FROM metrics m
                    WHERE m.user_id = %s AND m.verified = 1
                    ORDER BY m.score DESC
                    LIMIT 10
                    """
                    cursor.execute(query, (athlete['user_id'],))
                    metrics = cursor.fetchall()
                
                return {
                    "success": True,
                    "metrics": metrics
                }
            
            elif tool_name == "draft_email":
                recipient = tool_input["recipient"]
                purpose = tool_input.get("purpose", "introduction")

                # Get athlete metrics for personalization
                metrics_str = ""
                try:
                    with self.db.cursor() as cursor:
                        cursor.execute("""
                            SELECT title, value, unit FROM metrics
                            WHERE user_id = %s AND is_current = 1
                            ORDER BY percentile DESC LIMIT 5
                        """, (athlete['user_id'],))
                        top_metrics = cursor.fetchall()
                        if top_metrics:
                            metrics_str = "\n".join([f"- {m['title']}: {m['value']} {m.get('unit','')}" for m in top_metrics])
                except Exception:
                    pass

                # Return context for Claude to generate the actual email
                return {
                    "success": True,
                    "template_type": purpose,
                    "recipient": recipient,
                    "athlete_name": f"{athlete['first_name']} {athlete['last_name']}",
                    "position": athlete.get('position', 'N/A'),
                    "city": athlete.get('city', ''),
                    "state": athlete.get('state', ''),
                    "grad_year": athlete.get('graduation_year', 'TBD'),
                    "top_metrics": metrics_str or "No verified metrics available",
                    "instructions": "Generate a polished, personalized recruiting email using the athlete info above. Follow NCAA recruiting etiquette. Be professional but genuine. Include the athlete's key metrics. Vary tone by purpose: 'introduction' = formal first contact, 'camp follow-up' = reference specific camp attended, 'interest expression' = show knowledge of the program, 'visit request' = ask about unofficial/official visit."
                }
            
            elif tool_name == "match_programs":
                state = tool_input.get("state", None)
                limit = tool_input.get("limit", 15)
                result = self.recruiting_tools.match_programs(athlete, state=state, limit=limit)
                return result

            elif tool_name == "analyze_profile":
                result = self.recruiting_tools.analyze_profile(athlete)
                return result

            elif tool_name == "get_recruiting_calendar":
                sport = tool_input.get("sport", athlete.get('sport', 'football'))
                grad_year = tool_input.get("grad_year", athlete.get('graduation_year', 2026))
                query = f"NCAA {sport} recruiting calendar {grad_year} contact periods dead periods evaluation periods signing day"
                results = self.web_tools.search_web(query, max_results=8)
                return {
                    "success": True,
                    "sport": sport,
                    "grad_year": grad_year,
                    "results": results
                }

            elif tool_name == "get_film_guidance":
                position = tool_input.get("position", athlete.get('position', 'athlete'))
                query = f"{position} football highlight reel tips what coaches look for film breakdown Hudl 2025"
                results = self.web_tools.search_web(query, max_results=8)
                return {
                    "success": True,
                    "position": position,
                    "results": results
                }

            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_camp_cards(self, response_text: str, tool_results: list = None) -> Optional[Dict]:
        """
        Extract camp information - use ACTUAL URLs from search results
        Falls back to parsing response text if no tool results
        """
        camps = []
        
        # Try to get camps from tool results first (has real URLs!)
        if tool_results:
            for result in tool_results:
                if isinstance(result, dict) and result.get('camps'):
                    for camp in result['camps'][:5]:
                        camps.append({
                            "name": camp.get("name", "Camp"),
                            "url": camp.get("url", ""),
                            "description": camp.get("description", ""),
                            "type": "camp"
                        })
                    break  # Found camps, stop looking
        
        return {"camps": camps} if camps else None
    
    def _get_step_description(self, tool_name: str, tool_input: Dict) -> str:
        """Generate human-readable step description for UI"""
        if tool_name == "find_camps":
            location = tool_input.get("location", "nearby")
            return f"🔍 Searching for camps in {location}..."
        elif tool_name == "search_web":
            query = tool_input.get("query", "")
            return f"🌐 Researching: {query[:50]}..."
        elif tool_name == "get_athlete_stats":
            return "📊 Analyzing your metrics..."
        elif tool_name == "draft_email":
            return "✉️ Drafting email..."
        elif tool_name == "match_programs":
            state = tool_input.get("state", "nationwide")
            return f"🏫 Finding matching college programs ({state})..."
        elif tool_name == "analyze_profile":
            return "📈 Analyzing your recruiting profile vs position averages..."
        elif tool_name == "get_recruiting_calendar":
            return "📅 Looking up NCAA recruiting calendar..."
        elif tool_name == "get_film_guidance":
            pos = tool_input.get("position", "your position")
            return f"🎬 Getting film guidance for {pos}..."
        else:
            return f"🔧 Running {tool_name}..."

# Initialize orchestrator
orchestrator = OrchestratorAgent()

