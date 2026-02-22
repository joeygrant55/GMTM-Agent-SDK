"""
Reports API - Saved research reports from agent sessions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import json
import hmac
import hashlib
import base64
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["Reports"])


def _get_agent_db():
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor
    )


class ReportCreate(BaseModel):
    user_id: int
    conversation_id: Optional[int] = None
    report_type: str  # college_fit, profile_analysis, school_deep_dive, action_plan
    title: str
    content: str
    summary: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/reports/{user_id}")
async def list_reports(user_id: int, report_type: Optional[str] = None):
    """List all reports for an athlete"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            if report_type:
                c.execute("""
                    SELECT id, report_type, title, summary, created_at, updated_at
                    FROM agent_reports WHERE user_id = %s AND report_type = %s
                    ORDER BY created_at DESC
                """, (user_id, report_type))
            else:
                c.execute("""
                    SELECT id, report_type, title, summary, created_at, updated_at
                    FROM agent_reports WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
            reports = c.fetchall()
            for r in reports:
                r['created_at'] = str(r['created_at'])
                r['updated_at'] = str(r['updated_at'])
            return {"reports": reports}
    finally:
        db.close()


@router.get("/reports/{user_id}/{report_id}")
async def get_report(user_id: int, report_id: int):
    """Get a full report"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("""
                SELECT * FROM agent_reports WHERE id = %s AND user_id = %s
            """, (report_id, user_id))
            report = c.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
            report['created_at'] = str(report['created_at'])
            report['updated_at'] = str(report['updated_at'])
            return report
    finally:
        db.close()


@router.post("/reports")
async def create_report(request: ReportCreate):
    """Save a new report"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("""
                INSERT INTO agent_reports (user_id, conversation_id, report_type, title, content, summary, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                request.user_id,
                request.conversation_id,
                request.report_type,
                request.title,
                request.content,
                request.summary,
                json.dumps(request.metadata) if request.metadata else None
            ))
            db.commit()
            return {"id": c.lastrowid, "title": request.title}
    finally:
        db.close()


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    """Delete a report"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM agent_reports WHERE id = %s", (report_id,))
            db.commit()
            return {"deleted": True}
    finally:
        db.close()


# ============================================================
# SHAREABLE REPORT LINKS
# Token format: base64url(user_id:report_id) + "." + hmac[:12]
# No DB migration needed — token is self-contained and signed.
# ============================================================

def _get_share_secret() -> bytes:
    secret = os.getenv("SHARE_TOKEN_SECRET", "sparq-share-default-secret-change-in-prod")
    return secret.encode()


def _make_share_token(user_id: int, report_id: int) -> str:
    payload = f"{user_id}:{report_id}".encode()
    payload_b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    sig = hmac.new(_get_share_secret(), payload, hashlib.sha256).hexdigest()[:12]
    return f"{payload_b64}.{sig}"


def _decode_share_token(token: str) -> tuple[int, int]:
    """Returns (user_id, report_id) or raises HTTPException."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            raise ValueError("bad format")
        payload_b64, provided_sig = parts
        # Re-pad base64
        padding = 4 - len(payload_b64) % 4
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * (padding % 4))
        expected_sig = hmac.new(_get_share_secret(), payload, hashlib.sha256).hexdigest()[:12]
        if not hmac.compare_digest(provided_sig, expected_sig):
            raise ValueError("invalid signature")
        uid, rid = payload.decode().split(":")
        return int(uid), int(rid)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")


@router.get("/reports/{user_id}/{report_id}/share-token")
async def get_share_token(user_id: int, report_id: int):
    """Generate a shareable token for a report (no DB change needed)."""
    # Verify the report exists and belongs to this user
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, title FROM agent_reports WHERE id = %s AND user_id = %s",
                (report_id, user_id)
            )
            report = c.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
    finally:
        db.close()

    token = _make_share_token(user_id, report_id)
    base_url = os.getenv("FRONTEND_URL", "https://sparq-agent.vercel.app")
    return {
        "token": token,
        "url": f"{base_url}/report/{token}",
        "title": report["title"],
    }


@router.get("/reports/public/{token}")
async def get_public_report(token: str):
    """Fetch a report by share token — no auth required."""
    user_id, report_id = _decode_share_token(token)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("""
                SELECT r.id, r.report_type, r.title, r.content, r.summary,
                       r.created_at, u.first_name, u.last_name, u.position, u.sport,
                       u.graduation_year, u.city, u.state
                FROM agent_reports r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.id = %s AND r.user_id = %s
            """, (report_id, user_id))
            report = c.fetchone()
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
            report["created_at"] = str(report["created_at"])
            return report
    finally:
        db.close()
