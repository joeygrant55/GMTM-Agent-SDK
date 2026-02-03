"""
Reports API - Saved research reports from agent sessions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import json
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
