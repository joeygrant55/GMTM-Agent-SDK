# GMTM Agent SDK - Autonomous Marketing Agents
#
# This module contains Claude Agent SDK powered agents for:
# - Scout AI: Talent discovery for coaches/scouts
# - Content Pipeline: Auto-generate from Notion calendar
# - Event Factory: SPARQ events -> parallel content
# - Lead Qualification: B2B prospect research
# - Performance Dashboard: Real-time metrics
# - Orchestration Hub: Campaign coordination

# Note: Old Agent SDK imports commented out due to claude-agent-sdk dependency
# from .content_pipeline import run_content_pipeline
# from .scout_agent import run_scout_search, ScoutAgent
# from .query_builder import QueryBuilder, build_search_query

# New standalone agents (no SDK dependencies)
# from .camp_finder_standalone import CampFinderAgent

__all__ = [
    # 'run_content_pipeline',
    # 'run_scout_search',
    # 'ScoutAgent',
    # 'QueryBuilder',
    # 'build_search_query',
    # 'CampFinderAgent'
]
