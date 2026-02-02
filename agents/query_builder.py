"""
Query Builder
=============

Translates natural language search parameters into SQL queries for GMTM database.
Handles metric normalization, position mappings, and state abbreviations.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# ============================================
# METRIC MAPPINGS
# ============================================

# Maps natural language metric names to exact database titles
METRIC_MAPPINGS: Dict[str, str] = {
    # 40-yard dash variations
    "40": "40 Yard Dash",
    "40 yard": "40 Yard Dash",
    "40-yard": "40 Yard Dash",
    "40 yard dash": "40 Yard Dash",
    "40-yard dash": "40 Yard Dash",
    "forty": "40 Yard Dash",
    "forty yard": "40 Yard Dash",
    "forty yard dash": "40 Yard Dash",
    "40 time": "40 Yard Dash",

    # Vertical jump variations
    "vertical": "Vertical Jump",
    "vert": "Vertical Jump",
    "vertical jump": "Vertical Jump",
    "verticle": "Vertical Jump",  # Common typo

    # Shuttle variations
    "5-10-5": "5-10-5 shuttle",
    "5-10-5 shuttle": "5-10-5 shuttle",
    "shuttle": "5-10-5 shuttle",
    "pro agility": "5-10-5 shuttle",
    "20 yard shuttle": "20 Yard Shuttle",

    # Bench press variations
    "bench": "Bench Press",
    "bench press": "Bench Press",
    "185 bench": "185 Bench",
    "185": "185 Bench",
    "225 bench": "225 Pound Bench Press",
    "225": "225 Pound Bench Press",

    # Other strength metrics
    "squat": "Squat",
    "deadlift": "Deadlift",
    "clean": "Clean",
    "power clean": "Power Clean",

    # Size metrics
    "height": "Height",
    "weight": "Weight",
    "wingspan": "Wingspan",
    "hand size": "Hand Size",

    # Jump metrics
    "broad jump": "Broad Jump",
    "long jump": "Long Jump",
    "standing broad": "Broad Jump",

    # Volleyball specific
    "spike touch": "Spike Touch",
    "block touch": "Block Touch",
    "reach": "1-hand reach",
    "1-hand reach": "1-hand reach",
    "2-hand reach": "2-hand reach",

    # Speed metrics
    "100 meter": "100 Meter Dash",
    "100m": "100 Meter Dash",
    "speed": "Speed",

    # Academic
    "gpa": "GPA",
    "sat": "SAT",
    "act": "ACT",
}

# Metrics where lower is better (for sorting)
LOWER_IS_BETTER = {
    "40 Yard Dash",
    "5-10-5 shuttle",
    "20 Yard Shuttle",
    "100 Meter Dash",
    "Speed",
}

# ============================================
# POSITION MAPPINGS
# ============================================

# Maps position names/abbreviations to position_ids
POSITION_MAPPINGS: Dict[str, List[int]] = {
    # Football - Offense
    "quarterback": [211, 240, 302, 327],
    "qb": [211, 240, 302, 327],
    "running back": [243, 297, 317, 324],
    "rb": [243, 297, 317, 324],
    "halfback": [243, 319],
    "hb": [243, 319],
    "fullback": [249],
    "fb": [249],
    "wide receiver": [256, 311, 317, 321],
    "wr": [256, 311, 317, 321],
    "receiver": [256, 311, 317, 321],
    "tight end": [245],
    "te": [245],
    "offensive line": [264, 275, 244],
    "ol": [264, 275, 244],
    "offensive lineman": [264, 275, 244],
    "center": [265],
    "guard": [264, 282],
    "tackle": [244],
    "offensive tackle": [244],
    "ot": [244],

    # Football - Defense
    "linebacker": [223, 225, 236, 237, 297, 318, 327],
    "lb": [223, 225, 236, 237, 297, 318, 327],
    "middle linebacker": [223, 297],
    "mlb": [223, 297],
    "inside linebacker": [225],
    "ilb": [225],
    "outside linebacker": [237, 318, 327],
    "olb": [237, 318, 327],
    "defensive back": [226, 227, 233, 234],
    "db": [226, 227, 233, 234],
    "cornerback": [227, 302, 311, 321],
    "cb": [227, 302, 311, 321],
    "corner": [227, 302, 311, 321],
    "safety": [233, 234],
    "free safety": [233],
    "fs": [233],
    "strong safety": [234, 318],
    "ss": [234, 318],
    "defensive line": [214, 217, 219],
    "dl": [214, 217, 219],
    "defensive lineman": [214, 217, 219],
    "defensive end": [219, 307, 310, 322],
    "de": [219, 307, 310, 322],
    "defensive tackle": [214, 320],
    "dt": [214, 320],
    "nose guard": [320],
    "ng": [320],

    # Football - Special Teams
    "kicker": [259],
    "k": [259],
    "punter": [260],
    "p": [260],
    "long snapper": [261, 307],
    "ls": [261, 307],

    # Football - General
    "athlete": [253],
    "ath": [253],
    "dual": [212, 241],
}

# ============================================
# STATE MAPPINGS
# ============================================

STATE_MAPPINGS: Dict[str, str] = {
    # Full names to abbreviations
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",

    # Abbreviations (lowercase for matching)
    "al": "AL", "ak": "AK", "az": "AZ", "ar": "AR", "ca": "CA", "co": "CO",
    "ct": "CT", "de": "DE", "fl": "FL", "ga": "GA", "hi": "HI", "id": "ID",
    "il": "IL", "in": "IN", "ia": "IA", "ks": "KS", "ky": "KY", "la": "LA",
    "me": "ME", "md": "MD", "ma": "MA", "mi": "MI", "mn": "MN", "ms": "MS",
    "mo": "MO", "mt": "MT", "ne": "NE", "nv": "NV", "nh": "NH", "nj": "NJ",
    "nm": "NM", "ny": "NY", "nc": "NC", "nd": "ND", "oh": "OH", "ok": "OK",
    "or": "OR", "pa": "PA", "ri": "RI", "sc": "SC", "sd": "SD", "tn": "TN",
    "tx": "TX", "ut": "UT", "vt": "VT", "va": "VA", "wa": "WA", "wv": "WV",
    "wi": "WI", "wy": "WY", "dc": "DC",

    # Canadian provinces
    "ontario": "ON", "quebec": "QC", "british columbia": "BC", "alberta": "AB",
    "manitoba": "MB", "saskatchewan": "SK", "nova scotia": "NS",
    "new brunswick": "NB", "newfoundland": "NL", "prince edward island": "PE",
    "on": "ON", "qc": "QC", "bc": "BC", "ab": "AB", "mb": "MB", "sk": "SK",
}

# ============================================
# SPORT MAPPINGS
# ============================================

SPORT_MAPPINGS: Dict[str, int] = {
    "football": 1,
    "american football": 1,
    "basketball": 2,
    "wrestling": 3,
    "volleyball": 4,
    "baseball": 5,
    "soccer": 6,
    "lacrosse": 7,
    "golf": 8,
    "gymnastics": 9,
    "softball": 10,
    "swimming": 11,
    "track": 12,
    "track and field": 12,
    "hockey": 13,
    "ice hockey": 13,
    "field hockey": 14,
    "water polo": 15,
    "cheer": 16,
    "dance": 17,
    "cross country": 19,
    "xc": 19,
    "tennis": 22,
    "rugby": 21,
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class MetricFilter:
    """Represents a metric filter condition"""
    metric_name: str  # Database title
    operator: str  # <, >, <=, >=, =
    value: float
    alias: str  # For SQL alias


@dataclass
class SearchFilters:
    """Parsed search filters from natural language"""
    metrics: List[MetricFilter]
    positions: List[int]
    state: Optional[str]
    graduation_year: Optional[int]
    sport_id: Optional[int]
    limit: int = 10
    verified_only: bool = False


# ============================================
# QUERY BUILDER CLASS
# ============================================

class QueryBuilder:
    """Builds SQL queries from natural language parameters"""

    def __init__(self):
        pass

    def normalize_metric(self, metric: str) -> Optional[str]:
        """Convert natural language metric name to database title"""
        metric_lower = metric.lower().strip()
        return METRIC_MAPPINGS.get(metric_lower)

    def normalize_state(self, state: str) -> Optional[str]:
        """Convert state name/abbrev to standard abbreviation"""
        state_lower = state.lower().strip()
        return STATE_MAPPINGS.get(state_lower)

    def normalize_position(self, position: str) -> List[int]:
        """Convert position name to list of position IDs"""
        position_lower = position.lower().strip()
        return POSITION_MAPPINGS.get(position_lower, [])

    def normalize_sport(self, sport: str) -> Optional[int]:
        """Convert sport name to sport_id"""
        sport_lower = sport.lower().strip()
        return SPORT_MAPPINGS.get(sport_lower)

    def parse_metric_condition(self, text: str) -> Optional[MetricFilter]:
        """
        Parse a metric condition from text.

        Examples:
            "sub-4.5 40" -> MetricFilter("40 Yard Dash", "<", 4.5)
            "over 35 inch vertical" -> MetricFilter("Vertical Jump", ">", 35)
            "4.0 shuttle or better" -> MetricFilter("5-10-5 shuttle", "<", 4.0)
        """
        text_lower = text.lower()

        # Pattern: sub-X.X metric
        sub_pattern = r'sub[- ]?(\d+\.?\d*)\s*(?:second)?\s*(40|forty|vert|vertical|shuttle)'
        match = re.search(sub_pattern, text_lower)
        if match:
            value = float(match.group(1))
            metric_key = match.group(2)
            metric_name = self.normalize_metric(metric_key)
            if metric_name:
                return MetricFilter(
                    metric_name=metric_name,
                    operator="<",
                    value=value,
                    alias=self._make_alias(metric_name)
                )

        # Pattern: under/below X.X metric
        under_pattern = r'(?:under|below)\s+(\d+\.?\d*)\s*(?:second|s|inch|in)?\s*(40|forty|vert|vertical|shuttle|bench)'
        match = re.search(under_pattern, text_lower)
        if match:
            value = float(match.group(1))
            metric_key = match.group(2)
            metric_name = self.normalize_metric(metric_key)
            if metric_name:
                return MetricFilter(
                    metric_name=metric_name,
                    operator="<",
                    value=value,
                    alias=self._make_alias(metric_name)
                )

        # Pattern: over/above X metric
        over_pattern = r'(?:over|above)\s+(\d+\.?\d*)\s*(?:inch|in|"|\')?\s*(vert|vertical|broad|bench|height|weight)'
        match = re.search(over_pattern, text_lower)
        if match:
            value = float(match.group(1))
            metric_key = match.group(2)
            metric_name = self.normalize_metric(metric_key)
            if metric_name:
                return MetricFilter(
                    metric_name=metric_name,
                    operator=">",
                    value=value,
                    alias=self._make_alias(metric_name)
                )

        # Pattern: X.X 40/shuttle or better (for time metrics)
        better_pattern = r'(\d+\.?\d*)\s*(40|forty|shuttle|5-10-5)\s*(?:or better|or less)'
        match = re.search(better_pattern, text_lower)
        if match:
            value = float(match.group(1))
            metric_key = match.group(2)
            metric_name = self.normalize_metric(metric_key)
            if metric_name:
                return MetricFilter(
                    metric_name=metric_name,
                    operator="<=",
                    value=value,
                    alias=self._make_alias(metric_name)
                )

        return None

    def parse_graduation_year(self, text: str) -> Optional[int]:
        """Extract graduation year from text"""
        text_lower = text.lower()

        # Pattern: class of 20XX
        match = re.search(r'class\s+of\s+(\d{4})', text_lower)
        if match:
            return int(match.group(1))

        # Pattern: graduating 20XX
        match = re.search(r'(?:graduating|grad)\s+(\d{4})', text_lower)
        if match:
            return int(match.group(1))

        # Pattern: 20XX class/athletes/recruits
        match = re.search(r'(\d{4})\s+(?:class|athletes?|recruits?)', text_lower)
        if match:
            return int(match.group(1))

        # Pattern: standalone year (2024-2030 range)
        match = re.search(r'\b(202[4-9]|2030)\b', text_lower)
        if match:
            return int(match.group(1))

        return None

    def _make_alias(self, metric_name: str) -> str:
        """Create SQL-safe alias from metric name"""
        return re.sub(r'[^a-zA-Z0-9]', '_', metric_name.lower())[:20]

    def build_athlete_search_query(
        self,
        filters: SearchFilters,
        include_metrics: Optional[List[str]] = None
    ) -> str:
        """
        Build a complete SQL query for athlete search.

        Args:
            filters: Parsed search filters
            include_metrics: Additional metrics to include in SELECT

        Returns:
            SQL query string
        """
        # Base SELECT clause
        select_parts = [
            "u.user_id",
            "u.first_name",
            "u.last_name",
            "u.graduation_year",
            "u.avatar_uri",
            "l.city",
            "l.province",
            "l.country",
            "p.name as position_name",
            "s.name as sport_name",
            "(SELECT COUNT(*) FROM film f WHERE f.user_id = u.user_id AND f.visibility = 2) as film_count"
        ]

        # Metric JOINs and SELECTs
        metric_joins = []
        for mf in filters.metrics:
            join = f"""
LEFT JOIN metrics m_{mf.alias} ON u.user_id = m_{mf.alias}.user_id
    AND m_{mf.alias}.title = '{mf.metric_name}'
    AND m_{mf.alias}.is_current = 1"""
            metric_joins.append(join)
            select_parts.append(f"m_{mf.alias}.value as {mf.alias}")

        # Include additional metrics if requested
        if include_metrics:
            for metric_name in include_metrics:
                alias = self._make_alias(metric_name)
                if not any(mf.alias == alias for mf in filters.metrics):
                    join = f"""
LEFT JOIN metrics m_{alias} ON u.user_id = m_{alias}.user_id
    AND m_{alias}.title = '{metric_name}'
    AND m_{alias}.is_current = 1"""
                    metric_joins.append(join)
                    select_parts.append(f"m_{alias}.value as {alias}")

        # Build WHERE clause
        where_parts = [
            "u.type = 1",  # Athletes only
            "u.visibility = 2"  # Public profiles
        ]

        # State filter
        if filters.state:
            where_parts.append(f"l.province = '{filters.state}'")

        # Graduation year filter
        if filters.graduation_year:
            where_parts.append(f"u.graduation_year = {filters.graduation_year}")

        # Sport filter
        if filters.sport_id:
            where_parts.append(f"c.sport_id = {filters.sport_id}")

        # Position filter
        if filters.positions:
            pos_list = ",".join(str(p) for p in filters.positions)
            where_parts.append(f"up.position_id IN ({pos_list})")

        # Metric filters
        for mf in filters.metrics:
            where_parts.append(
                f"CAST(m_{mf.alias}.value AS DECIMAL(10,2)) {mf.operator} {mf.value}"
            )

        # Verified only filter
        if filters.verified_only:
            for mf in filters.metrics:
                where_parts.append(f"m_{mf.alias}.verified = 1")

        # Build ORDER BY (sort by first metric if exists)
        order_by = ""
        if filters.metrics:
            first_metric = filters.metrics[0]
            direction = "ASC" if first_metric.metric_name in LOWER_IS_BETTER else "DESC"
            order_by = f"ORDER BY CAST(m_{first_metric.alias}.value AS DECIMAL(10,2)) {direction}"

        # Assemble query
        query = f"""
SELECT DISTINCT
    {', '.join(select_parts)}
FROM users u
JOIN locations l ON u.location_id = l.location_id
LEFT JOIN career c ON u.user_id = c.user_id AND c.is_current = 1 AND c.visibility = 1
LEFT JOIN user_positions up ON c.career_id = up.career_id
LEFT JOIN positions p ON up.position_id = p.position_id
LEFT JOIN sports s ON c.sport_id = s.sport_id
{chr(10).join(metric_joins)}
WHERE {' AND '.join(where_parts)}
{order_by}
LIMIT {filters.limit}
"""
        return query.strip()


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def build_search_query(
    state: Optional[str] = None,
    position: Optional[str] = None,
    graduation_year: Optional[int] = None,
    sport: Optional[str] = None,
    metric_filters: Optional[List[Tuple[str, str, float]]] = None,
    limit: int = 10,
    verified_only: bool = False
) -> str:
    """
    Convenience function to build a search query.

    Args:
        state: State name or abbreviation
        position: Position name or abbreviation
        graduation_year: 4-digit year
        sport: Sport name
        metric_filters: List of (metric_name, operator, value) tuples
        limit: Max results
        verified_only: Only verified metrics

    Returns:
        SQL query string
    """
    builder = QueryBuilder()

    # Normalize inputs
    normalized_state = builder.normalize_state(state) if state else None
    position_ids = builder.normalize_position(position) if position else []
    sport_id = builder.normalize_sport(sport) if sport else None

    # Build metric filters
    metrics = []
    if metric_filters:
        for metric_name, operator, value in metric_filters:
            db_name = builder.normalize_metric(metric_name)
            if db_name:
                metrics.append(MetricFilter(
                    metric_name=db_name,
                    operator=operator,
                    value=value,
                    alias=builder._make_alias(db_name)
                ))

    filters = SearchFilters(
        metrics=metrics,
        positions=position_ids,
        state=normalized_state,
        graduation_year=graduation_year,
        sport_id=sport_id,
        limit=limit,
        verified_only=verified_only
    )

    return builder.build_athlete_search_query(filters)


# ============================================
# LOCAL TESTING
# ============================================

if __name__ == "__main__":
    # Test query building
    query = build_search_query(
        state="Texas",
        position="running back",
        metric_filters=[
            ("40", "<", 4.5),
            ("vertical", ">", 35)
        ],
        limit=5
    )
    print("Generated Query:")
    print(query)
