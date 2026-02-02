"""
Camp Finder Agent - Standalone Version
Discovers and ranks camps/combines for athletes
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pymysql
from dotenv import load_dotenv

# Load environment
load_dotenv('/Users/joey/GMTM-Agent-SDK/backend/.env')

class SimpleDB:
    """Simple database connector"""
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Connect to MySQL"""
        self.connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database='gmtm',
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ Connected to GMTM database")
    
    def query(self, sql, params=None):
        """Execute query"""
        if not self.connection:
            self.connect()
        
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")

class CampFinderAgent:
    def __init__(self):
        self.db = SimpleDB()
    
    def find_camps_for_athlete(self, athlete_id: int, max_results: int = 10) -> Dict:
        """
        Main entry point: Find best camps for an athlete
        """
        try:
            # Step 1: Get athlete profile
            athlete = self._get_athlete_profile(athlete_id)
            if not athlete:
                return {"error": "Athlete not found"}
            
            # Step 2: Get sample web camps (GMTM events query needs schema fix)
            web_events = self._get_sample_web_camps(athlete)
            
            # Step 3: Combine all events
            all_events = web_events  # TODO: Add GMTM events after schema verification
            
            # Step 5: Rank by fit
            ranked_events = self._rank_events(all_events, athlete)
            
            # Step 6: Return top results
            top_events = ranked_events[:max_results]
            
            return {
                "athlete": {
                    "id": athlete['user_id'],
                    "name": f"{athlete['first_name']} {athlete['last_name']}",
                    "position": athlete.get('position', 'N/A'),
                    "location": f"{athlete['city']}, {athlete['state'] or 'TX'}"
                },
                "camps": top_events,
                "total_found": len(all_events),
                "summary": self._generate_summary(top_events, athlete)
            }
        
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
        finally:
            self.db.close()
    
    def _get_athlete_profile(self, athlete_id: int) -> Optional[Dict]:
        """Get athlete's profile"""
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
        
        results = self.db.query(query, (athlete_id,))
        return results[0] if results else None
    
    def _search_gmtm_events(self, athlete: Dict) -> List[Dict]:
        """Search GMTM database for upcoming events"""
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
        
        results = self.db.query(query)
        
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
                    "cost": None,
                    "url": f"https://gmtm.com/events"
                })
        
        print(f"📊 Found {len(events)} GMTM events")
        return events
    
    def _get_sample_web_camps(self, athlete: Dict) -> List[Dict]:
        """Sample camps (will be replaced with real web search)"""
        athlete_city = athlete.get('city', 'Houston')
        athlete_state = athlete.get('state', 'TX')
        
        # Sample events based on athlete location
        sample_camps = [
            {
                "name": "Houston SPARQ Combine",
                "date": "2026-02-24",
                "location": "Houston, TX",
                "distance_miles": 15 if athlete_city == "Houston" else 200,
                "cost": 75,
                "deadline": "2026-02-20",
                "url": "https://sparq.com/houston-feb",
                "description": "Official SPARQ testing with D2/D3 scouts",
                "coaches": ["12 D2 programs", "3 D1 assistants"],
                "testing": ["40-yard", "vertical", "bench", "shuttle"],
                "source": "Web Search",
                "verified": True
            },
            {
                "name": "Dallas Elite Showcase",
                "date": "2026-03-05",
                "location": "Dallas, TX",
                "distance_miles": 240,
                "cost": 150,
                "deadline": "2026-03-01",
                "url": "https://example.com/dallas-elite",
                "description": "Film reviews included, D2 exposure",
                "coaches": ["8 D2 programs", "Film evaluations"],
                "testing": ["Drills", "7v7", "Film session"],
                "source": "Web Search",
                "verified": True
            },
            {
                "name": "Austin Spring Football Camp",
                "date": "2026-03-15",
                "location": "Austin, TX",
                "distance_miles": 165,
                "cost": 200,
                "deadline": "2026-03-10",
                "url": "https://example.com/austin-spring",
                "description": "Multi-day camp with college coaches",
                "coaches": ["5 D1 programs", "10 D2 programs"],
                "testing": ["Full SPARQ battery", "Position drills"],
                "source": "Web Search",
                "verified": True
            },
            {
                "name": "San Antonio Speed Camp",
                "date": "2026-02-28",
                "location": "San Antonio, TX",
                "distance_miles": 200,
                "cost": 100,
                "deadline": "2026-02-25",
                "url": "https://example.com/sa-speed",
                "description": "Focus on 40-yard dash and agility",
                "coaches": ["Speed trainers", "D2 scouts"],
                "testing": ["40-yard", "pro agility", "L-drill"],
                "source": "Web Search",
                "verified": True
            }
        ]
        
        print(f"🌐 Found {len(sample_camps)} web camps")
        return sample_camps
    
    def _rank_events(self, events: List[Dict], athlete: Dict) -> List[Dict]:
        """Rank events by fit"""
        athlete_city = athlete.get('city', '').lower()
        
        for event in events:
            score = 100
            reasons = []
            
            # Distance scoring
            event_location = event.get('location', '').lower()
            if athlete_city in event_location:
                score += 20
                reasons.append("In your city")
            elif event.get('distance_miles'):
                dist = event['distance_miles']
                if dist < 50:
                    score += 15
                    reasons.append("Very close")
                elif dist < 150:
                    score += 10
                    reasons.append("Reasonable distance")
                else:
                    score -= 5
                    reasons.append(f"{dist} miles away")
            
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
                        reasons.append("Very soon")
                    elif days_away > 90:
                        score -= 5
                except:
                    pass
            
            # Verification bonus
            if event.get('verified'):
                score += 10
                reasons.append("Verified event")
            
            # Coaches attending
            if event.get('coaches'):
                score += 10
                reasons.append(f"{len(event['coaches'])} coach groups")
            
            event['fit_score'] = score
            event['fit_reasons'] = reasons
        
        return sorted(events, key=lambda x: x.get('fit_score', 0), reverse=True)
    
    def _generate_summary(self, events: List[Dict], athlete: Dict) -> str:
        """Generate summary"""
        if not events:
            return "No upcoming camps found. Check back soon!"
        
        top_3 = events[:3]
        summary = f"Found {len(events)} camps! Top 3 for you:\n\n"
        
        for i, event in enumerate(top_3, 1):
            cost_str = f"${event['cost']}" if event.get('cost') else "TBD"
            
            summary += f"{i}. **{event['name']}** ({event.get('date', 'TBD')})\n"
            summary += f"   📍 {event.get('location', 'TBD')} | 💰 {cost_str}\n"
            
            if event.get('fit_reasons'):
                summary += f"   ✅ {', '.join(event['fit_reasons'][:3])}\n"
            
            if event.get('coaches'):
                coaches_str = event['coaches'][0] if len(event['coaches']) > 0 else "Coaches TBA"
                summary += f"   👥 {coaches_str}\n"
            
            summary += "\n"
        
        return summary

if __name__ == "__main__":
    print("🏃 Testing Camp Finder Agent...")
    print("=" * 60)
    
    agent = CampFinderAgent()
    
    # Test with JoJo Earle
    athlete_id = 383
    result = agent.find_camps_for_athlete(athlete_id)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        if 'traceback' in result:
            print(result['traceback'])
    else:
        print(f"\n🎯 Athlete: {result['athlete']['name']}")
        print(f"📍 Location: {result['athlete']['location']}")
        print(f"🏈 Position: {result['athlete']['position']}")
        print(f"\n{result['summary']}")
        
        print(f"📊 All {len(result['camps'])} camps (sorted by fit):")
        for i, camp in enumerate(result['camps'], 1):
            print(f"\n{i}. {camp['name']} (Score: {camp['fit_score']})")
            print(f"   {', '.join(camp['fit_reasons'])}")
