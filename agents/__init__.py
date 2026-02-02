# GMTM Agent SDK - Autonomous Marketing Agents
#
# This module contains Claude Agent SDK powered agents for:
# - Scout AI: Talent discovery for coaches/scouts
# - Content Pipeline: Auto-generate from Notion calendar
# - Event Factory: SPARQ events -> parallel content
# - Lead Qualification: B2B prospect research
# - Performance Dashboard: Real-time metrics
# - Orchestration Hub: Campaign coordination

from .content_pipeline import run_content_pipeline
from .scout_agent import run_scout_search, ScoutAgent
from .query_builder import QueryBuilder, build_search_query
# from .event_factory import run_event_factory
# from .lead_qualification import run_lead_qualification
# from .performance_dashboard import run_performance_dashboard
# from .orchestration_hub import run_orchestration_hub

__all__ = [
    'run_content_pipeline',
    'run_scout_search',
    'ScoutAgent',
    'QueryBuilder',
    'build_search_query',
    # 'run_event_factory',
    # 'run_lead_qualification',
    # 'run_performance_dashboard',
    # 'run_orchestration_hub'
]
