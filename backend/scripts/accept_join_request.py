#!/usr/bin/env python3
"""
Run to accept a join request and decrement the team's required_size if available.
Usage:
  python scripts/accept_join_request.py 3
  python scripts/accept_join_request.py 3 --no-decrement
"""
import argparse
import sys
import os
# ensure project root is on sys.path so `from db import db` works when running the script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from db import db

parser = argparse.ArgumentParser(description="Accept a join_request by id")
parser.add_argument('id', type=int, help='join_request id')
parser.add_argument('--no-decrement', action='store_true', help='Do not decrement team required_size')
args = parser.parse_args()

cur = db.cursor(dictionary=True)
cur.execute("SELECT id,status,team_request_id FROM join_requests WHERE id=%s", (args.id,))
row = cur.fetchone()
if not row:
    print(f"join_request id={args.id} not found")
    cur.close()
    sys.exit(1)

print('Before:', row)
try:
    cur.execute("UPDATE join_requests SET status='accepted' WHERE id=%s", (args.id,))
    if not args.no_decrement and row.get('team_request_id'):
        cur.execute(
            "UPDATE team_requests SET required_size = required_size - 1 WHERE id=%s AND required_size > 0",
            (row['team_request_id'],)
        )
    db.commit()
except Exception as e:
    print('Error during update:', e)
    db.rollback()
    cur.close()
    sys.exit(1)

cur.execute("SELECT id,status,team_request_id FROM join_requests WHERE id=%s", (args.id,))
print('After :', cur.fetchone())
cur.close()
print('Done')
