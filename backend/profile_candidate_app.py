"""Explicit profile-value app; no legacy profile/recruiting routers are mounted.

Uses the same reviewed candidate configuration and authentication boundary.
Import/startup does not read a profile, prepare schema or call a model. The
profile summary is deterministic; combine help is not exposed in this app.
"""
from candidate_app import create_app

app = create_app(surface="profile")
