#!/usr/bin/env python3
"""Serve the current review package on loopback, without stale browser caches."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ReviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def send_head(self):
        # Never answer 304 for an asset that the artist may have just replaced.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        return super().send_head()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(ReviewHandler, directory=str(ROOT))) as server:
        print(f"SIDEY preview: http://127.0.0.1:{args.port}/ — {ROOT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
