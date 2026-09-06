#!/usr/bin/env python3
import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/intent-ledger/ledger.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS intents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim TEXT NOT NULL,
            source TEXT NOT NULL,
            dependency TEXT,
            status TEXT DEFAULT 'pending',
            agent TEXT,
            timestamp TEXT,
            mode TEXT DEFAULT 'alert',
            evidence TEXT,
            expires_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_claim(claim, source, agent=None, dependency=None, mode="alert", evidence=None, expires_in_days=7):
    expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO intents (claim, source, dependency, agent, timestamp, mode, evidence, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (claim, source, dependency, agent, datetime.now().isoformat(), mode, evidence, expires_at))
    conn.commit()
    conn.close()
    print(f"✅ Claim added: {claim[:50]}... (expires: {expires_in_days} days)")

def check_expired():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        SELECT id, claim, expires_at FROM intents WHERE expires_at < ? AND status != 'completed'
    ''', (now,))
    expired = c.fetchall()
    for row in expired:
        c.execute('UPDATE intents SET status = ? WHERE id = ?', ('expired', row[0]))
    conn.commit()
    conn.close()
    if expired:
        print(f"⚠️ Marked {len(expired)} expired claims.")

def check_conflicts(claim):
    check_expired()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, claim, source, dependency, status, agent, mode, evidence, expires_at FROM intents
        WHERE claim LIKE ? AND status NOT IN ('completed', 'expired')
    ''', (f'%{claim}%',))
    results = c.fetchall()
    conn.close()
    if results:
        print(f"⚠️ Active conflicts found for '{claim}':")
        for r in results:
            expires = r[8][:10] if r[8] else "never"
            print(f"  - #{r[0]}: {r[1][:40]}... | agent: {r[5] or 'unknown'} | expires: {expires}")
            if r[6] == "quarantine":
                print(f"    🔒 QUARANTINED — requires review")
            elif r[6] == "rebase":
                print(f"    🔄 REBASE — auto-update")
            else:
                print(f"    🔔 ALERT — warning only")
    else:
        print(f"✅ No active conflicts found for '{claim}'")
    return results

def list_intents(limit=10):
    check_expired()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, claim, source, status, mode, agent, expires_at FROM intents
        ORDER BY id DESC LIMIT ?
    ''', (limit,))
    results = c.fetchall()
    conn.close()
    print(f"{'ID':<4} {'Claim':<35} {'Status':<12} {'Mode':<12} {'Agent':<15} {'Expires':<12}")
    print("-" * 90)
    for r in results:
        expires = r[6][:10] if r[6] else "never"
        print(f"{r[0]:<4} {r[1][:35]:<35} {r[3]:<12} {r[4]:<12} {str(r[5])[:15]:<15} {expires:<12}")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) < 2:
        print("Usage: intent_ledger.py [add|check|list] ...")
        print("  add <claim> <source> [--agent NAME] [--mode alert|quarantine|rebase] [--evidence URL] [--expires DAYS]")
        print("  check <claim>")
        print("  list")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "add":
        claim = sys.argv[2]
        source = sys.argv[3]
        agent = None
        mode = "alert"
        evidence = None
        expires = 7
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--agent" and i+1 < len(sys.argv):
                agent = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == "--mode" and i+1 < len(sys.argv):
                mode = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == "--evidence" and i+1 < len(sys.argv):
                evidence = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == "--expires" and i+1 < len(sys.argv):
                expires = int(sys.argv[i+1])
                i += 2
            else:
                i += 1
        add_claim(claim, source, agent, mode=mode, evidence=evidence, expires_in_days=expires)
    elif cmd == "check" and len(sys.argv) >= 3:
        check_conflicts(sys.argv[2])
    elif cmd == "list":
        list_intents()
    else:
        print("Unknown command")

def export_intents(filename="intents_export.json"):
    check_expired()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM intents ORDER BY id DESC')
    results = c.fetchall()
    conn.close()
    data = []
    for r in results:
        data.append({
            "id": r[0],
            "claim": r[1],
            "source": r[2],
            "dependency": r[3],
            "status": r[4],
            "agent": r[5],
            "timestamp": r[6],
            "mode": r[7],
            "evidence": r[8],
            "expires_at": r[9]
        })
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Exported {len(data)} intents to {filename}")

def import_intents(filename="intents_export.json"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    with open(filename, 'r') as f:
        data = json.load(f)
    count = 0
    for item in data:
        c.execute('''
            INSERT INTO intents (claim, source, dependency, status, agent, timestamp, mode, evidence, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item.get('claim'), item.get('source'), item.get('dependency'),
              item.get('status', 'pending'), item.get('agent'),
              item.get('timestamp', datetime.now().isoformat()),
              item.get('mode', 'alert'), item.get('evidence'),
              item.get('expires_at')))
        count += 1
    conn.commit()
    conn.close()
    print(f"✅ Imported {count} intents from {filename}")
