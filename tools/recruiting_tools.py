"""
Recruiting Tools - Database queries for athlete matching and analysis
"""

import os
import pymysql
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
load_dotenv()


class RecruitingTools:
    """Database-powered recruiting intelligence"""
    
    def __init__(self):
        self.db = None
    
    def _connect(self):
        if not self.db or not self.db.open:
            self.db = pymysql.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database='gmtm',
                port=3306,
                cursorclass=pymysql.cursors.DictCursor
            )
    
    def _close(self):
        if self.db:
            self.db.close()
            self.db = None
    
    def match_programs(self, athlete: Dict, state: str = None, limit: int = 15, preferences: Dict = None) -> Dict:
        """Find college programs that match athlete's profile"""
        try:
            self._connect()
            with self.db.cursor() as c:
                sport = athlete.get('sport', 'Football (American)')
                state = athlete.get('state', '')
                position = athlete.get('position', '')
                
                # Find programs that have recruited similar athletes
                # Look at scholarship offers from athletes at same position
                c.execute("""
                    SELECT DISTINCT o.organization_id, o.name, o.type,
                           l.city, l.province as state,
                           COUNT(so.scholarship_offer_id) as offer_count
                    FROM scholarship_offers so
                    JOIN teams t ON so.team_id = t.team_id
                    JOIN organizations o ON t.organization_id = o.organization_id
                    LEFT JOIN locations l ON o.location_id = l.location_id
                    WHERE o.type = 1
                    GROUP BY o.organization_id, o.name, o.type, l.city, l.province
                    ORDER BY offer_count DESC
                    LIMIT 20
                """)
                top_programs = c.fetchall()
                
                # If state filter provided
                region = state or (preferences.get('region') if preferences else None)
                if region:
                    c.execute("""
                        SELECT DISTINCT o.organization_id, o.name,
                               l.city, l.province as state,
                               COUNT(so.scholarship_offer_id) as offer_count
                        FROM scholarship_offers so
                        JOIN teams t ON so.team_id = t.team_id
                        JOIN organizations o ON t.organization_id = o.organization_id
                        LEFT JOIN locations l ON o.location_id = l.location_id
                        WHERE o.type = 1 AND l.province = %s
                        GROUP BY o.organization_id, o.name, l.city, l.province
                        ORDER BY offer_count DESC
                        LIMIT 10
                    """, (region,))
                    regional_programs = c.fetchall()
                else:
                    regional_programs = []
                
                return {
                    "success": True,
                    "top_programs": [
                        {
                            "name": p["name"],
                            "city": p.get("city", ""),
                            "state": p.get("state", ""),
                            "offers_given": p["offer_count"]
                        } for p in top_programs
                    ],
                    "regional_programs": [
                        {
                            "name": p["name"],
                            "city": p.get("city", ""),
                            "state": p.get("state", ""),
                            "offers_given": p["offer_count"]
                        } for p in regional_programs
                    ],
                    "athlete_position": position,
                    "athlete_state": state
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self._close()
    
    def analyze_profile(self, athlete: Dict, position: str = None) -> Dict:
        """Analyze athlete's metrics compared to peers"""
        try:
            user_id = athlete.get('user_id') if isinstance(athlete, dict) else athlete
            if not position and isinstance(athlete, dict):
                position = athlete.get('position')
            self._connect()
            with self.db.cursor() as c:
                # Get athlete's metrics
                c.execute("""
                    SELECT title, value, unit, verified, percentile
                    FROM metrics
                    WHERE user_id = %s AND is_current = 1
                    ORDER BY title
                """, (user_id,))
                athlete_metrics = c.fetchall()
                
                if not athlete_metrics:
                    return {"success": False, "error": "No metrics found for this athlete"}
                
                # Get averages for key metrics across all athletes
                key_metrics = ['40 Yard Dash', 'Vertical Jump', 'Bench Press', 
                              'Squat', '5-10-5 shuttle', 'Height', 'Weight',
                              'Broad Jump', 'Power Toss']
                
                analysis = []
                for metric in athlete_metrics:
                    title = metric['title']
                    try:
                        athlete_val = float(metric['value'])
                    except (ValueError, TypeError):
                        analysis.append({
                            "metric": title,
                            "value": metric['value'],
                            "unit": metric.get('unit', ''),
                            "comparison": "N/A"
                        })
                        continue
                    
                    # Get average for this metric
                    c.execute("""
                        SELECT AVG(CAST(value AS DECIMAL(10,2))) as avg_val,
                               COUNT(*) as total,
                               MIN(CAST(value AS DECIMAL(10,2))) as min_val,
                               MAX(CAST(value AS DECIMAL(10,2))) as max_val
                        FROM metrics
                        WHERE title = %s AND is_current = 1 
                        AND value REGEXP '^[0-9]'
                    """, (title,))
                    avg_row = c.fetchone()
                    
                    # Calculate percentile (how many are worse)
                    if title in ['40 Yard Dash', '5-10-5 shuttle']:
                        # Lower is better for time-based metrics
                        c.execute("""
                            SELECT COUNT(*) as worse
                            FROM metrics
                            WHERE title = %s AND is_current = 1 
                            AND value REGEXP '^[0-9]'
                            AND CAST(value AS DECIMAL(10,2)) > %s
                        """, (title, athlete_val))
                    else:
                        # Higher is better for distance/weight metrics
                        c.execute("""
                            SELECT COUNT(*) as worse
                            FROM metrics
                            WHERE title = %s AND is_current = 1 
                            AND value REGEXP '^[0-9]'
                            AND CAST(value AS DECIMAL(10,2)) < %s
                        """, (title, athlete_val))
                    
                    worse_count = c.fetchone()['worse']
                    total = avg_row['total'] if avg_row['total'] else 1
                    percentile = round((worse_count / total) * 100)
                    
                    # Determine strength/weakness
                    if percentile >= 80:
                        rating = "Elite"
                    elif percentile >= 60:
                        rating = "Above Average"
                    elif percentile >= 40:
                        rating = "Average"
                    elif percentile >= 20:
                        rating = "Below Average"
                    else:
                        rating = "Needs Work"
                    
                    analysis.append({
                        "metric": title,
                        "value": metric['value'],
                        "unit": metric.get('unit', ''),
                        "average": round(float(avg_row['avg_val']), 2) if avg_row['avg_val'] else None,
                        "percentile": percentile,
                        "rating": rating,
                        "total_athletes": total
                    })
                
                # Identify strengths and weaknesses
                strengths = [a for a in analysis if a.get('percentile', 0) >= 70]
                weaknesses = [a for a in analysis if a.get('percentile', 0) <= 30 and a.get('percentile') is not None]
                
                return {
                    "success": True,
                    "metrics": analysis,
                    "strengths": [s['metric'] for s in strengths],
                    "weaknesses": [w['metric'] for w in weaknesses],
                    "overall_rating": "Strong" if len(strengths) > len(weaknesses) else "Developing"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self._close()
    
    def get_scholarship_offers(self, user_id: int) -> Dict:
        """Get scholarship offers for an athlete"""
        try:
            self._connect()
            with self.db.cursor() as c:
                c.execute("""
                    SELECT o.name as school, so.status, so.created_on
                    FROM scholarship_offers so
                    JOIN teams t ON so.team_id = t.team_id
                    JOIN organizations o ON t.organization_id = o.organization_id
                    WHERE so.user_id = %s
                    ORDER BY so.created_on DESC
                """, (user_id,))
                offers = c.fetchall()
                
                status_map = {
                    0: "Pending", 1: "Offered", 2: "Verbal Commit",
                    3: "Official Visit", 4: "Signed", 5: "Interested",
                    6: "Committed", 9: "Declined"
                }
                
                return {
                    "success": True,
                    "total_offers": len(offers),
                    "offers": [
                        {
                            "school": o["school"],
                            "status": status_map.get(o["status"], f"Status {o['status']}"),
                            "date": str(o["created_on"]) if o["created_on"] else None
                        } for o in offers
                    ]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self._close()


recruiting_tools = RecruitingTools()
