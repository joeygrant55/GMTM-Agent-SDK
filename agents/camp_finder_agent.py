"""
Camp Finder Agent
Discovers and ranks camps/combines for athletes
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_research_tools import web_tools
from agents.db_connector import get_db

class CampFinderAgent:
    def __init__(self):
        self.db = None
        self.web_tools = web_tools
    
    def connect_db(self):
        """Connect to GMTM database"""
        if not self.db:
            self.db = get_db()
    
    def find_camps_for_athlete(self, athlete_id: int, max_results: int = 10) -> Dict:
        """
        Main entry point: Find best camps for an athlete
        
        Returns:
        {
            "athlete": {...},
            "camps": [{...}],
            "summary": "Found X camps..."
        }
        """
        try:
            self.connect_db()
            
            # Step 1: Get athlete profile
            athlete = self._get_athlete_profile(athlete_id)
            if not athlete:
                return {"error": "Athlete not found"}
            
            # Step 2: Search GMTM events
            gmtm_events = self._search_gmtm_events(athlete)
            
            # Step 3: Search web for additional camps
            web_events = self._search_web_camps(athlete)
            
            # Step 4: Combine and deduplicate
            all_events = gmtm_events + web_events
            
            # Step 5: Rank by fit
            ranked_events = self._rank_events(all_events, athlete)
            
            # Step 6: Return top results
            top_events = ranked_events[:max_results]
            
            return {
                "athlete": {
                    "id": athlete['user_id'],
                    "name": f"{athlete['first_name']} {athlete['last_name']}",
                    "position": athlete.get('position', 'N/A'),
                    "location": f"{athlete['city']}, {athlete['state']}"
                },
                "camps": top_events,
                "total_found": len(all_events),
                "summary": self._generate_summary(top_events, athlete)
            }
        
        except Exception as e:
            return {"error": str(e)}
        finally:
            if self.db:
                self.db.disconnect()
    
    def _get_athlete_profile(self, athlete_id: int) -> Optional[Dict]:
        """Get athlete's profile from database"""
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
        
        results = self.db.execute_query(query, (athlete_id,))
        return results[0] if results else None
    
    def _search_gmtm_events(self, athlete: Dict) -> List[Dict]:
        """Search GMTM database for events"""
        # Query GMTM events table
        query = """
        SELECT 
            ipe.name,
            ipe.date,
            l.city,
            l.province as state,
            ipe.description
        FROM in_person_events ipe
        LEFT JOIN locations l ON ipe.location_id = l.location_id
        WHERE ipe.date >= CURDATE()
        AND ipe.date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)
        ORDER BY ipe.date
        LIMIT 20
        """
        
        results = self.db.execute_query(query)
        
        # Format results
        events = []
        for row in results:
            if row['name'] and row['date']:
                events.append({
                    "name": row['name'],
                    "date": str(row['date']),
                    "location": f"{row['city']}, {row['state']}" if row['city'] else "TBD",
                    "source": "GMTM Database",
                    "verified": True,
                    "description": row.get('description', ''),
                    "cost": None,  # Not in GMTM data
                    "url": f"https://gmtm.com/events/{row['name'].lower().replace(' ', '-')}"
                })
        
        return events
    
    def _search_web_camps(self, athlete: Dict) -> List[Dict]:
        """Search web for camps"""
        sport = athlete.get('sport', 'Football')
        position = athlete.get('position', '')
        location = athlete.get('city', 'Houston')
        
        # Use web research tools
        web_events = self.web_tools.search_camps(
            sport=sport,
            position=position,
            location=location,
            radius_miles=150
        )
        
        # Format and verify
        verified_events = []
        for event in web_events:
            verification = self.web_tools.verify_event_legitimacy(event)
            if verification['legitimate']:
                event['legitimacy_check'] = verification
                event['source'] = 'Web Search'
                verified_events.append(event)
        
        return verified_events
    
    def _rank_events(self, events: List[Dict], athlete: Dict) -> List[Dict]:
        """
        Rank events by fit for athlete
        Scoring factors:
        - Distance (closer = better)
        - Cost (lower = better)
        - Timing (sooner but not too soon)
        - Level match
        - Legitimacy
        """
        athlete_city = athlete.get('city', 'Houston')
        
        for event in events:
            score = 100  # Start at 100
            reasons = []
            
            # Distance scoring
            event_location = event.get('location', '')
            if athlete_city.lower() in event_location.lower():
                score += 20
                reasons.append("In your city")
            elif event.get('distance_miles'):
                if event['distance_miles'] < 50:
                    score += 15
                    reasons.append("Very close")
                elif event['distance_miles'] < 150:
                    score += 10
                    reasons.append("Reasonable distance")
                else:
                    score -= 10
                    reasons.append("Far from home")
            
            # Cost scoring
            cost = event.get('cost')
            if cost:
                if cost < 100:
                    score += 15
                    reasons.append("Affordable")
                elif cost < 200:
                    score += 5
                elif cost > 300:
                    score -= 15
                    reasons.append("Expensive")
            
            # Timing scoring
            if event.get('date'):
                try:
                    event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                    days_away = (event_date - datetime.now()).days
                    
                    if 14 <= days_away <= 45:
                        score += 15
                        reasons.append("Good timing")
                    elif days_away < 7:
                        score -= 10
                        reasons.append("Very soon - may be too late")
                    elif days_away > 90:
                        score -= 5
                        reasons.append("Far in future")
                except:
                    pass
            
            # Verification bonus
            if event.get('verified'):
                score += 10
                reasons.append("Verified event")
            
            # Coaches attending
            if event.get('coaches'):
                score += 10
                reasons.append("College coaches attending")
            
            # Testing/evaluation
            if event.get('testing'):
                score += 5
                reasons.append("Official testing")
            
            event['fit_score'] = score
            event['fit_reasons'] = reasons
        
        # Sort by score (highest first)
        return sorted(events, key=lambda x: x.get('fit_score', 0), reverse=True)
    
    def _generate_summary(self, events: List[Dict], athlete: Dict) -> str:
        """Generate human-readable summary"""
        if not events:
            return "No upcoming camps found in your area. Check back soon!"
        
        top_3 = events[:3]
        
        summary = f"Found {len(events)} camps for you! Top recommendations:\n\n"
        
        for i, event in enumerate(top_3, 1):
            cost_str = f"${event['cost']}" if event.get('cost') else "TBD"
            date_str = event.get('date', 'TBD')
            location = event.get('location', 'TBD')
            
            summary += f"{i}. **{event['name']}** ({date_str})\n"
            summary += f"   📍 {location} | 💰 {cost_str}\n"
            
            if event.get('fit_reasons'):
                summary += f"   ✅ {', '.join(event['fit_reasons'][:3])}\n"
            
            if event.get('coaches'):
                summary += f"   👥 {', '.join(event['coaches'][:2])}\n"
            
            summary += f"   🔗 {event.get('url', 'N/A')}\n\n"
        
        return summary

# Initialize agent
camp_finder = CampFinderAgent()

if __name__ == "__main__":
    # Test with a real athlete
    print("🏃 Testing Camp Finder Agent...")
    print("=" * 60)
    
    athlete_id = 383  # JoJo Earle
    result = camp_finder.find_camps_for_athlete(athlete_id)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"🎯 Athlete: {result['athlete']['name']}")
        print(f"📍 Location: {result['athlete']['location']}")
        print(f"🏈 Position: {result['athlete']['position']}\n")
        print(result['summary'])
        
        print(f"\n📊 Details for top {len(result['camps'])} camps:")
        for camp in result['camps']:
            print(f"\n{camp['name']} (Score: {camp['fit_score']})")
            print(f"  Reasons: {', '.join(camp['fit_reasons'])}")
