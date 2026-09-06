#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/intent-ledger/ledger.db")
app = FastAPI(title="Intent Ledger API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Intent(BaseModel):
    claim: str
    source: str
    dependency: Optional[str] = None
    agent: Optional[str] = None
    mode: str = "alert"
    evidence: Optional[str] = None
    expires_days: int = 7

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"message": "Intent Ledger API", "endpoints": ["/intents", "/intents/{id}", "/conflicts/{claim}"]}

@app.get("/intents", response_model=List[dict])
def list_intents(limit: int = 20):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, claim, source, dependency, status, agent, mode, evidence, expires_at
        FROM intents ORDER BY id DESC LIMIT ?
    ''', (limit,))
    results = c.fetchall()
    conn.close()
    return [dict(row) for row in results]

@app.post("/intents")
def create_intent(intent: Intent):
    conn = get_db()
    c = conn.cursor()
    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(days=intent.expires_days)).isoformat()
    c.execute('''
        INSERT INTO intents (claim, source, dependency, agent, mode, evidence, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (intent.claim, intent.source, intent.dependency, intent.agent, intent.mode, intent.evidence, expires_at))
    conn.commit()
    intent_id = c.lastrowid
    conn.close()
    return {"id": intent_id, "message": "Intent created"}

@app.get("/conflicts/{claim}")
def check_conflicts(claim: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, claim, source, agent, mode, status FROM intents
        WHERE claim LIKE ? AND status NOT IN ('completed', 'expired')
    ''', (f'%{claim}%',))
    results = c.fetchall()
    conn.close()
    return {"claim": claim, "conflicts": [dict(row) for row in results]}

@app.get("/webui", response_class=HTMLResponse)
def web_ui():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Intent Ledger</title>
    <style>
        body { font-family: monospace; max-width: 1200px; margin: 40px auto; padding: 20px; background: #0d1117; color: #e6edf3; }
        h1 { color: #58a6ff; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #30363d; }
        th { background: #161b22; color: #8b949e; }
        .status-pending { color: #d29922; }
        .status-completed { color: #3fb950; }
        .status-expired { color: #f85149; }
        .mode-alert { color: #d29922; }
        .mode-quarantine { color: #f85149; }
        .mode-rebase { color: #58a6ff; }
    </style>
    </head>
    <body>
    <h1>🔍 Intent Ledger</h1>
    <p>Track and coordinate agent intents.</p>
    <div id="intents">Loading...</div>
    <script>
        fetch('/intents?limit=50')
            .then(r => r.json())
            .then(data => {
                let html = '<table><tr><th>ID</th><th>Claim</th><th>Agent</th><th>Status</th><th>Mode</th><th>Source</th></tr>';
                data.forEach(i => {
                    html += `<tr>
                        <td>${i.id}</td>
                        <td>${i.claim.substring(0, 50)}${i.claim.length > 50 ? '...' : ''}</td>
                        <td>${i.agent || 'unknown'}</td>
                        <td class="status-${i.status}">${i.status}</td>
                        <td class="mode-${i.mode}">${i.mode}</td>
                        <td>${i.source.substring(0, 30)}${i.source.length > 30 ? '...' : ''}</td>
                    </tr>`;
                });
                html += '</table>';
                document.getElementById('intents').innerHTML = html;
            });
    </script>
    </body>
    </html>
    '''
