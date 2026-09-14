#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "ledger.db"
API_KEYS = {"vantaforgeai": "sk_vanta_pF5SSP9U36B5W98eRHDICkWt_f_VTScH"}

app = FastAPI(title="Intent Ledger API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in API_KEYS.values():
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

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
def root():
    return {"message": "Intent Ledger API - Authentication Required"}

@app.get("/intents")
def list_intents(limit: int = 20, api_key: str = Depends(verify_api_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM intents ORDER BY id DESC LIMIT ?', (limit,))
    results = c.fetchall()
    conn.close()
    return [dict(row) for row in results]

@app.post("/intents")
def create_intent(intent: Intent, api_key: str = Depends(verify_api_key)):
    conn = get_db()
    c = conn.cursor()
    expires_at = (datetime.now() + timedelta(days=intent.expires_days)).isoformat()
    c.execute('INSERT INTO intents (claim, source, dependency, agent, mode, evidence, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (intent.claim, intent.source, intent.dependency, intent.agent, intent.mode, intent.evidence, expires_at))
    conn.commit()
    conn.close()
    return {"message": "Intent created"}

@app.get("/webui", response_class=HTMLResponse)
def web_ui():
    return '''<!DOCTYPE html><html><head><title>Intent Ledger</title>
<style>body{font-family:monospace;max-width:1200px;margin:40px auto;padding:20px;background:#0d1117;color:#e6edf3}
h1{color:#58a6ff}table{width:100%;border-collapse:collapse;margin:20px 0}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}
th{background:#161b22;color:#8b949e}
.status-pending{color:#d29922}.status-completed{color:#3fb950}.status-expired{color:#f85149}
.mode-alert{color:#d29922}.mode-quarantine{color:#f85149}.mode-rebase{color:#58a6ff}
.auth-box{background:#161b22;padding:20px;border-radius:8px;margin:20px 0}
input,button{padding:8px 12px;border-radius:4px;border:1px solid #30363d;background:#0d1117;color:#e6edf3}
button{background:#238636;cursor:pointer}
</style></head><body>
<h1>Intent Ledger</h1>
<div class="auth-box"><label>API Key: <input type="text" id="apiKey" placeholder="Enter API key" style="width:300px"></label>
<button onclick="load()">Load</button></div>
<div id="intents">Enter API key and click Load.</div>
<script>
function load(){var k=document.getElementById('apiKey').value;if(!k){document.getElementById('intents').innerHTML='Please enter API key.';return}
document.getElementById('intents').innerHTML='Loading...'
fetch('/intents',{headers:{'X-API-Key':k}}).then(r=>{if(!r.ok)throw new Error('Unauthorized');return r.json()})
.then(d=>{var h='<table><tr><th>ID</th><th>Claim</th><th>Agent</th><th>Status</th><th>Mode</th></tr>'
d.forEach(i=>{h+='<tr><td>'+i.id+'</td><td>'+(i.claim||'').substring(0,50)+'</td><td>'+(i.agent||'unknown')+'</td><td class="status-'+i.status+'">'+i.status+'</td><td class="mode-'+i.mode+'">'+i.mode+'</td></tr>'})
h+='</table>';document.getElementById('intents').innerHTML=h})
.catch(e=>{document.getElementById('intents').innerHTML='Error: '+e.message})}
</script></body></html>'''
