"""
NFL Combine Benchmark Agent
===========================

Compares SPARQ athlete metrics to NFL Combine prospects.
Returns percentile rankings and notable player comparisons.
Also compares to historical SPARQ data from NFL players' high school testing.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Paths to data files
DATA_PATH = Path(__file__).parent.parent / "data" / "nfl_combine_data.json"
SPARQ_DATA_PATH = Path(__file__).parent.parent / "data" / "sparq_historical_data.json"


@dataclass
class MetricComparison:
    """Comparison result for a single metric."""
    metric_name: str
    athlete_value: float
    nfl_percentile: int
    better_than: List[str]  # "Player Name (value)"
    similar_to: List[str]
    worse_than: List[str]


@dataclass
class NFLComparison:
    """Complete NFL comparison result."""
    position: str
    overall_percentile: int
    metrics: Dict[str, MetricComparison]
    pro_comparison: str
    headline: str


def load_nfl_data() -> Dict[str, Any]:
    """Load NFL Combine data from JSON file."""
    with open(DATA_PATH, 'r') as f:
        return json.load(f)


def load_sparq_data() -> Dict[str, Any]:
    """Load historical SPARQ data from JSON file."""
    try:
        with open(SPARQ_DATA_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"athletes": [], "percentile_benchmarks": {}}


def find_sparq_comparisons(
    athlete_metrics: Dict[str, float],
    position: str = "WR"
) -> Dict[str, Any]:
    """
    Find NFL players who had similar SPARQ metrics in high school.

    Returns:
        Dict with similar_profiles and sparq_percentile
    """
    data = load_sparq_data()
    sparq_athletes = data.get('athletes', [])
    benchmarks = data.get('percentile_benchmarks', {})

    if not sparq_athletes:
        return {"similar_profiles": [], "sparq_percentile": None, "sparq_headline": None}

    # Filter by position if enough data
    position_athletes = [a for a in sparq_athletes if a.get('position') == position]
    if len(position_athletes) < 5:
        position_athletes = sparq_athletes

    # Calculate similarity scores based on available metrics
    scored_athletes = []
    for athlete in position_athletes:
        if not athlete.get('sparq_score'):
            continue

        similarity = 0
        matches = 0

        # Compare each metric
        for metric in ['forty', 'vertical', 'shuttle']:
            athlete_val = athlete_metrics.get(metric)
            sparq_val = athlete.get(metric)
            if athlete_val and sparq_val:
                # Calculate percentage difference
                diff = abs(athlete_val - sparq_val) / sparq_val
                if diff < 0.05:  # Within 5%
                    similarity += 3
                elif diff < 0.10:  # Within 10%
                    similarity += 2
                elif diff < 0.15:  # Within 15%
                    similarity += 1
                matches += 1

        if matches >= 2:
            scored_athletes.append({
                "name": athlete['name'],
                "college": athlete.get('college', ''),
                "position": athlete.get('position', ''),
                "sparq_score": athlete['sparq_score'],
                "draft_class": athlete.get('draft_class'),
                "similarity": similarity / matches if matches else 0
            })

    # Sort by similarity and get top matches
    scored_athletes.sort(key=lambda x: x['similarity'], reverse=True)
    similar_profiles = scored_athletes[:5]

    # Calculate SPARQ percentile based on athlete's metrics
    sparq_scores = [a['sparq_score'] for a in sparq_athletes if a.get('sparq_score')]

    # Estimate athlete's SPARQ score from their metrics (simplified formula)
    estimated_sparq = None
    if athlete_metrics.get('forty') and athlete_metrics.get('vertical'):
        # Rough approximation based on the SPARQ formula patterns
        forty = athlete_metrics['forty']
        vertical = athlete_metrics['vertical']
        shuttle = athlete_metrics.get('shuttle', 4.2)

        # Higher vertical, lower times = higher score
        estimated_sparq = (vertical * 2.5) + ((5.0 - forty) * 40) + ((4.5 - shuttle) * 20)
        estimated_sparq = max(50, min(155, estimated_sparq))  # Clamp to realistic range

    sparq_percentile = None
    if estimated_sparq and sparq_scores:
        better_count = sum(1 for s in sparq_scores if s < estimated_sparq)
        sparq_percentile = int((better_count / len(sparq_scores)) * 100)
        sparq_percentile = min(99, max(1, sparq_percentile))

    # Generate SPARQ headline
    sparq_headline = None
    if similar_profiles:
        top_match = similar_profiles[0]
        sparq_headline = f"Similar athletic profile to {top_match['name']} ({top_match['college']}) - NFL Draft Class {top_match['draft_class']}"

    return {
        "similar_profiles": similar_profiles,
        "sparq_percentile": sparq_percentile,
        "estimated_sparq": round(estimated_sparq, 2) if estimated_sparq else None,
        "sparq_headline": sparq_headline
    }


def calculate_percentile(value: float, values: List[float], lower_is_better: bool = False) -> int:
    """
    Calculate percentile rank for a value within a distribution.

    Args:
        value: The athlete's value
        values: List of NFL combine values
        lower_is_better: True for times (40, shuttle), False for jumps

    Returns:
        Percentile (0-100)
    """
    if not values:
        return 50

    if lower_is_better:
        # For times: count how many NFL players are SLOWER
        better_count = sum(1 for v in values if v > value)
    else:
        # For jumps: count how many NFL players have LOWER values
        better_count = sum(1 for v in values if v < value)

    percentile = int((better_count / len(values)) * 100)
    return min(99, max(1, percentile))


def find_player_comparisons(
    value: float,
    athletes: List[Dict],
    metric_key: str,
    lower_is_better: bool = False,
    limit: int = 3
) -> tuple[List[str], List[str], List[str]]:
    """
    Find players the athlete is better than, similar to, and worse than.

    Returns:
        Tuple of (better_than, similar_to, worse_than) lists
    """
    better_than = []
    similar_to = []
    worse_than = []

    # Tolerance for "similar" (within 2% for times, 5% for measurements)
    tolerance = 0.02 if lower_is_better else 0.05

    for athlete in athletes:
        nfl_value = athlete.get(metric_key)
        if nfl_value is None:
            continue

        name = athlete['name']
        diff = abs(value - nfl_value) / nfl_value if nfl_value else 0

        if diff < tolerance:
            similar_to.append(f"{name} ({nfl_value})")
        elif lower_is_better:
            if value < nfl_value:
                better_than.append(f"{name} ({nfl_value}s)")
            else:
                worse_than.append(f"{name} ({nfl_value}s)")
        else:
            if value > nfl_value:
                better_than.append(f"{name} ({nfl_value}\")")
            else:
                worse_than.append(f"{name} ({nfl_value}\")")

    return (
        better_than[:limit],
        similar_to[:limit],
        worse_than[:limit]
    )


def generate_pro_comparison(metrics: Dict[str, MetricComparison], position: str) -> str:
    """Generate a natural language pro comparison based on metrics."""

    # Find strongest metrics (highest percentiles)
    sorted_metrics = sorted(
        [(k, v) for k, v in metrics.items() if v.nfl_percentile],
        key=lambda x: x[1].nfl_percentile,
        reverse=True
    )

    if not sorted_metrics:
        return "Solid athletic profile across multiple metrics."

    top_metric = sorted_metrics[0]

    # Generate comparison based on top metric and position
    comparisons = {
        "WR": {
            "forty": "explosive speed reminiscent of speedster receivers",
            "vertical": "leaping ability similar to contested-catch specialists",
            "shuttle": "quick-twitch agility like slot receivers",
            "broad": "explosive lower body power for YAC ability"
        },
        "RB": {
            "forty": "breakaway speed that creates big play potential",
            "vertical": "explosive hips that translate to cuts and power",
            "shuttle": "lateral quickness for making defenders miss",
            "broad": "explosive leg drive for contact balance"
        },
        "QB": {
            "forty": "mobility that extends plays and creates rushing threat",
            "vertical": "athleticism that adds another dimension",
            "shuttle": "pocket movement skills to avoid pressure"
        },
        "CB": {
            "forty": "recovery speed to stick with any receiver",
            "vertical": "ball-hawking ability at the catch point",
            "shuttle": "hip fluidity to mirror routes"
        }
    }

    metric_name = top_metric[0]
    pos_comps = comparisons.get(position, comparisons.get("WR", {}))
    comp_text = pos_comps.get(metric_name, "well-rounded athletic ability")

    if top_metric[1].nfl_percentile >= 90:
        return f"Elite {comp_text}. Pro-ready athleticism."
    elif top_metric[1].nfl_percentile >= 75:
        return f"Above-average {comp_text}. Strong NFL projection."
    else:
        return f"Solid {comp_text}. Room to develop."


def generate_headline(metrics: Dict[str, MetricComparison], position: str) -> str:
    """Generate a shareable headline for the comparison."""

    # Find the most impressive comparison
    best_comparison = None
    best_percentile = 0

    for metric_name, comparison in metrics.items():
        if comparison.nfl_percentile > best_percentile and comparison.better_than:
            best_percentile = comparison.nfl_percentile
            best_comparison = comparison

    if best_comparison and best_comparison.better_than:
        famous_player = best_comparison.better_than[0].split(" (")[0]
        metric_display = best_comparison.metric_name.replace("_", " ").title()
        return f"Your {metric_display} is faster than {famous_player}'s at the NFL Combine"

    if best_percentile >= 90:
        return f"Your athleticism ranks in the top 10% of NFL {position} prospects"
    elif best_percentile >= 75:
        return f"Your metrics compare favorably to NFL {position} prospects"
    else:
        return f"See how you stack up against NFL {position} prospects"


def compare_to_nfl(
    athlete_metrics: Dict[str, float],
    position: str = "WR"
) -> Dict[str, Any]:
    """
    Compare an athlete's metrics to NFL Combine data.

    Args:
        athlete_metrics: Dict with keys like "forty", "vertical", "broad", "shuttle", "three_cone"
        position: Position to compare against (WR, RB, QB, etc.)

    Returns:
        Complete comparison data
    """
    data = load_nfl_data()
    nfl_athletes = data['athletes']

    # Filter to position (or all if position not found)
    position_athletes = [a for a in nfl_athletes if a.get('position') == position]
    if len(position_athletes) < 10:
        position_athletes = nfl_athletes  # Fall back to all positions

    # Metric configurations
    metric_configs = {
        "forty": {"key": "forty", "lower_is_better": True, "display": "40-Yard Dash"},
        "vertical": {"key": "vertical", "lower_is_better": False, "display": "Vertical Jump"},
        "broad": {"key": "broad", "lower_is_better": False, "display": "Broad Jump"},
        "shuttle": {"key": "shuttle", "lower_is_better": True, "display": "Shuttle"},
        "three_cone": {"key": "three_cone", "lower_is_better": True, "display": "3-Cone Drill"}
    }

    comparisons = {}
    percentiles = []

    for metric_name, config in metric_configs.items():
        athlete_value = athlete_metrics.get(metric_name)
        if athlete_value is None:
            continue

        # Get NFL values for this metric
        nfl_values = [a.get(config['key']) for a in position_athletes if a.get(config['key']) is not None]

        if not nfl_values:
            continue

        # Calculate percentile
        percentile = calculate_percentile(
            athlete_value,
            nfl_values,
            config['lower_is_better']
        )
        percentiles.append(percentile)

        # Find player comparisons
        better_than, similar_to, worse_than = find_player_comparisons(
            athlete_value,
            position_athletes,
            config['key'],
            config['lower_is_better']
        )

        comparisons[metric_name] = MetricComparison(
            metric_name=config['display'],
            athlete_value=athlete_value,
            nfl_percentile=percentile,
            better_than=better_than,
            similar_to=similar_to,
            worse_than=worse_than
        )

    # Calculate overall percentile (average of all metrics)
    overall_percentile = int(sum(percentiles) / len(percentiles)) if percentiles else 50

    # Generate text comparisons
    pro_comparison = generate_pro_comparison(comparisons, position)
    headline = generate_headline(comparisons, position)

    # Get SPARQ historical comparisons
    sparq_data = find_sparq_comparisons(athlete_metrics, position)

    # Convert to serializable dict
    return {
        "position": position,
        "overall_percentile": overall_percentile,
        "metrics": {k: asdict(v) for k, v in comparisons.items()},
        "pro_comparison": pro_comparison,
        "headline": headline,
        "sparq_comparison": sparq_data
    }


# Convenience function for the API
async def get_nfl_comparison(
    forty: Optional[float] = None,
    vertical: Optional[float] = None,
    broad: Optional[float] = None,
    shuttle: Optional[float] = None,
    three_cone: Optional[float] = None,
    position: str = "WR"
) -> Dict[str, Any]:
    """
    Async wrapper for NFL comparison.

    Args:
        forty: 40-yard dash time in seconds (e.g., 4.5)
        vertical: Vertical jump in inches (e.g., 38.0)
        broad: Broad jump in inches (e.g., 125)
        shuttle: Shuttle time in seconds (e.g., 4.2)
        three_cone: 3-cone drill time in seconds (e.g., 7.0)
        position: Position for comparison (WR, RB, QB, CB, etc.)

    Returns:
        NFL comparison result
    """
    # Build metrics dict from non-None values
    metric_names = ["forty", "vertical", "broad", "shuttle", "three_cone"]
    metric_values = [forty, vertical, broad, shuttle, three_cone]
    metrics = {k: v for k, v in zip(metric_names, metric_values) if v is not None}

    return compare_to_nfl(metrics, position)


# Testing
if __name__ == "__main__":
    # Test with Chapman Beaird's metrics
    result = compare_to_nfl(
        athlete_metrics={
            "forty": 4.636,
            "vertical": 38.2,
            "broad": 123,
            "shuttle": 4.349
        },
        position="WR"
    )
    print(json.dumps(result, indent=2))
