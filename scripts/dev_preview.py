"""Development-only preview adapter; accepts the managed preview CLI's flags."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import app

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")))
parser.add_argument("--strictPort", action="store_true", help="Accepted for preview compatibility; Flask never selects a fallback port.")
args = parser.parse_args()
app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
