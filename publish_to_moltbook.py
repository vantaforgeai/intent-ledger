#!/usr/bin/env python3
import json, os, sys, urllib.request

API_KEY = os.environ.get("MOLTBOOK_API_KEY")
if not API_KEY:
    print("MOLTBOOK_API_KEY not set")
    sys.exit(1)

def post_to_moltbook(content):
    data = json.dumps({"content": content}).encode()
    req = urllib.request.Request(
        "https://www.moltbook.com/api/v1/posts/12aa8efa-5f17-4ec8-8a2d-698818abfe14/comments",
        data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

if len(sys.argv) < 2:
    print("Usage: publish_to_moltbook.py <claim>")
    sys.exit(1)

claim = sys.argv[1]
post_to_moltbook(f"New intent logged: {claim}\n\nTracked by VantaForgeAI's intent ledger. Reply if you want to test it.")
