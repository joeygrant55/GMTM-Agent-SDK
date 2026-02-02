# SPARQ Agent SDK - Full Architecture

**Current Status:** Simple Python scripts (proof-of-concept)  
**Goal:** Full Agent SDK with autonomous web access

---

## What We Have Now (Phase 0)

### Current Architecture:
```
Frontend (Next.js)
    ↓ HTTP
Backend (FastAPI)
    ↓ Direct Python call
Simple Script (camp_finder_standalone.py)
    ↓ SQL query
GMTM Database
    ↓ Return hardcoded + DB data
```

### Limitations:
- ❌ Hardcoded camp data (sample list)
- ❌ Can't search the web
- ❌ Can't scrape websites
- ❌ Can't make autonomous decisions
- ❌ Limited to what's in our database

### Good For:
- ✅ Proof-of-concept (works NOW)
- ✅ Fast to build (1 hour)
- ✅ Easy to test
- ✅ No external dependencies

---

## What Full Agent SDK Gives You (Phase 1)

### Real Agent SDK Architecture:
```
Frontend (Next.js)
    ↓ HTTP
Backend (FastAPI)
    ↓ Spawn agent
Agent SDK (Claude + Tools)
    ├─ Tool: web_search() → Google/Brave Search
    ├─ Tool: scrape_page() → Any website
    ├─ Tool: call_api() → Any REST API
    ├─ Tool: query_database() → GMTM DB
    ├─ Tool: send_email() → SMTP/SendGrid
    └─ Tool: research() → Multi-step autonomous research
```

### What It Can Do:
- ✅ **Autonomous web research** - Searches Google, scrapes sites, evaluates legitimacy
- ✅ **Real-time data** - Always finds latest camps, not hardcoded
- ✅ **Makes decisions** - "Is this camp legit?" "Is this a good fit?"
- ✅ **Multi-step reasoning** - "Find camps → verify legitimacy → check coach reviews → rank by fit"
- ✅ **Calls any API** - MaxPreps, 247Sports, college APIs, etc.
- ✅ **Scrapes any site** - College athletic pages, camp registration sites
- ✅ **Not limited to our data** - Full internet access

---

## Example: Camp Finder with Full Agent SDK

### Current (Simple Script):
```python
def find_camps(athlete_id):
    athlete = db.query("SELECT * FROM users WHERE id = %s", athlete_id)
    
    # Hardcoded camps
    camps = [
        {"name": "Houston SPARQ", "cost": 75, ...},
        {"name": "Dallas Elite", "cost": 150, ...}
    ]
    
    # Simple ranking
    for camp in camps:
        camp['fit_score'] = calculate_fit(athlete, camp)
    
    return sorted(camps, key='fit_score')
```

**Problem:** Only knows about 4 hardcoded camps. Can't find new camps.

---

### With Full Agent SDK:
```python
from anthropic import Anthropic
from agent_sdk import Agent, Tool

# Define tools the agent can use
tools = [
    Tool(
        name="search_web",
        description="Search Google for camps and events",
        function=search_web  # Uses Google Custom Search API
    ),
    Tool(
        name="scrape_page",
        description="Extract data from a web page",
        function=scrape_page  # Uses BeautifulSoup/Playwright
    ),
    Tool(
        name="verify_legitimacy",
        description="Check if a camp is legitimate (reviews, history)",
        function=verify_legitimacy
    ),
    Tool(
        name="query_gmtm",
        description="Query GMTM database for athlete/event data",
        function=query_gmtm
    ),
    Tool(
        name="calculate_distance",
        description="Calculate distance between two locations",
        function=calculate_distance  # Uses geocoding API
    )
]

# Create agent
agent = Agent(
    model="claude-sonnet-4",
    tools=tools,
    system_prompt="""
    You are a Camp Discovery Agent. Your job is to find the best camps for an athlete.
    
    Process:
    1. Get athlete's profile (position, location, grad year, metrics)
    2. Search web for: "[sport] camps [location] [year]"
    3. Scrape camp pages for details (cost, date, coaches, testing)
    4. Verify legitimacy (check reviews, official sites, past attendees)
    5. Calculate distance from athlete
    6. Rank by fit (distance, cost, level, timing, legitimacy)
    7. Return top 10 with reasoning
    
    Be thorough. Don't just return obvious camps - find hidden gems too.
    """
)

def find_camps(athlete_id):
    # Agent autonomously:
    # - Queries GMTM DB for athlete
    # - Searches web for camps
    # - Scrapes 20+ camp websites
    # - Verifies legitimacy
    # - Calculates fit scores
    # - Returns ranked results
    
    result = agent.run(
        prompt=f"Find the best camps for athlete {athlete_id}"
    )
    
    return result.output
```

**Result:** Finds 50+ real camps across the web, verifies them, ranks by fit. Always up-to-date.

---

## Tools Available in Full Agent SDK

### Research & Data Collection:
- `search_web(query)` - Google/Brave search
- `scrape_page(url)` - Extract content from any site
- `call_api(endpoint, method, params)` - REST API calls
- `query_database(sql)` - GMTM database access
- `geocode(address)` - Location data
- `calculate_distance(from, to)` - Distance calculation

### Communication:
- `send_email(to, subject, body)` - Email outreach
- `draft_email(recipient, context)` - Generate email text
- `post_social(platform, content)` - Social media posting
- `send_sms(to, message)` - Text messages

### Analysis:
- `analyze_roster(school)` - College roster analysis
- `check_reviews(camp_name)` - Reputation check
- `compare_metrics(athlete1, athlete2)` - Performance comparison
- `predict_fit(athlete, program)` - Recruiting fit score

### File Operations:
- `read_file(path)` - Read local files
- `write_file(path, content)` - Save results
- `create_pdf(data)` - Generate reports

---

## Implementation Options

### Option A: Claude Agent SDK (Anthropic's official)
```bash
pip install anthropic
pip install anthropic-agent-sdk
```

**Pros:**
- Official Anthropic support
- Well-documented
- Computer Use tool included
- Robust error handling

**Cons:**
- Newer, less community resources
- Requires Anthropic API key

---

### Option B: LangChain Agents
```bash
pip install langchain langchain-anthropic
```

**Pros:**
- Mature ecosystem
- Many pre-built tools
- Large community
- Can switch LLM providers

**Cons:**
- More complex setup
- Sometimes overkill for simple agents

---

### Option C: Custom Agent Framework (what we'd build)
```python
# Lightweight custom implementation
class Agent:
    def __init__(self, model, tools):
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
    
    def run(self, prompt):
        while True:
            response = self.model.generate(prompt)
            
            if response.tool_calls:
                # Execute tools
                for call in response.tool_calls:
                    result = self.tools[call.name](call.params)
                    prompt += f"\nTool result: {result}"
            else:
                return response.text
```

**Pros:**
- Full control
- No dependencies
- Exactly what we need

**Cons:**
- More initial work
- We maintain it

---

## Recommended Approach

### Phase 1: Hybrid (Keep it working, add autonomy)

**Keep:**
- Current simple scripts (they work!)
- Direct database access
- FastAPI backend

**Add:**
- Real web search (Brave Search API)
- Web scraping (BeautifulSoup + Playwright)
- Agent decision-making (Claude API)

**Architecture:**
```python
# camp_finder_agent_v2.py

class CampFinderAgentV2:
    def __init__(self):
        self.db = get_db()
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    def find_camps(self, athlete_id):
        # 1. Get athlete from DB (still direct query - fast)
        athlete = self.get_athlete(athlete_id)
        
        # 2. Search web for camps (NEW - agent autonomy)
        web_camps = self.search_web_autonomously(athlete)
        
        # 3. Agent ranks and explains (NEW - AI decision making)
        ranked = self.rank_with_reasoning(athlete, web_camps)
        
        return ranked
    
    def search_web_autonomously(self, athlete):
        """Agent searches web and scrapes camp pages"""
        prompt = f"""
        Find upcoming {athlete['sport']} camps near {athlete['city']}, {athlete['state']}.
        
        Steps:
        1. Search Google for: "{athlete['sport']} camps {athlete['state']} 2026"
        2. Scrape top 20 results for camp details
        3. Extract: name, date, cost, location, coaches, registration URL
        4. Verify legitimacy (check domain, reviews)
        5. Return structured data
        
        Athlete context:
        - Position: {athlete['position']}
        - Grad year: {athlete['graduation_year']}
        - Location: {athlete['city']}, {athlete['state']}
        """
        
        response = self.anthropic.messages.create(
            model="claude-sonnet-4",
            max_tokens=4096,
            tools=[
                self.tool_search_web,
                self.tool_scrape_page,
                self.tool_extract_camp_details
            ],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Agent autonomously searches and scrapes
        return response.content
```

**Benefits:**
- ✅ Still fast (database queries direct)
- ✅ Now finds REAL camps from web
- ✅ Agent makes decisions about legitimacy
- ✅ Always up-to-date
- ✅ Not limited to our data

---

## Real Tools to Add

### 1. Web Search (Brave Search API)
```python
import requests

def search_web(query: str, max_results: int = 20):
    """Search the web using Brave Search API"""
    headers = {"X-Subscription-Token": os.getenv("BRAVE_API_KEY")}
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params={"q": query, "count": max_results}
    )
    return response.json()["web"]["results"]
```

**Cost:** ~$5/month for 2000 queries  
**Sign up:** https://brave.com/search/api/

---

### 2. Web Scraping (Playwright)
```python
from playwright.sync_api import sync_playwright

def scrape_page(url: str):
    """Extract content from a web page"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        
        # Extract camp details
        details = {
            "title": page.title(),
            "content": page.content(),
            "links": [a.get_attribute("href") for a in page.query_selector_all("a")]
        }
        
        browser.close()
        return details
```

**Cost:** Free (open source)

---

### 3. Claude API with Tools
```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

tools = [
    {
        "name": "search_web",
        "description": "Search the web for information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4",
    max_tokens=4096,
    tools=tools,
    messages=[{"role": "user", "content": "Find football camps in Texas"}]
)

# Agent autonomously calls search_web() tool
```

**Cost:** ~$3 per 1M input tokens, ~$15 per 1M output tokens

---

## Next Steps

**Option 1: Quick Win (2-3 hours)**
- Add Brave Search API
- Add basic web scraping
- Keep simple Python scripts
- Now finds real camps from web

**Option 2: Full Agent SDK (1-2 days)**
- Implement Claude Agent SDK
- Add all research tools
- Autonomous multi-step reasoning
- Full web access

**Option 3: Hybrid Best-of-Both (4-6 hours)**
- Keep fast database queries
- Add agent for web research
- Agent makes ranking decisions
- Still works if agent fails

---

## My Recommendation: Option 3 (Hybrid)

**Why:**
- ✅ Keeps what works (database queries)
- ✅ Adds autonomy where it matters (web research)
- ✅ Graceful degradation (works even if API fails)
- ✅ Fast to build (today!)
- ✅ Easy to test incrementally

**Implementation:**
1. Add Brave Search API (30 min)
2. Add web scraping with Playwright (1 hour)
3. Wrap in Claude agent (2 hours)
4. Test with real athletes (1 hour)

**Total:** ~4-5 hours to full autonomous camp discovery

---

**Ready to upgrade to full Agent SDK power?** Let me know and I'll start building it!
