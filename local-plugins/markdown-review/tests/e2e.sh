#!/usr/bin/env bash
set -euo pipefail

# Resolve plugin root (parent of tests/) so this script works from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PLUGIN_ROOT"

WORK="$(mktemp -d -t mdreview-e2e.XXXXXX)"
LOG="$WORK/server.log"
FIXTURE="$WORK/fixture.md"
SIDECAR="$FIXTURE.comments.json"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    sleep 0.2
    kill -KILL "$SERVER_PID" 2>/dev/null || true
  fi
  # Clean up the lock file if it points to our PID.
  LOCK_PATH="${HOME}/.cache/markdown-review/lock.json"
  if [[ -f "$LOCK_PATH" ]]; then
    OWNER_PID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$LOCK_PATH" 2>/dev/null || echo "")"
    if [[ -n "$OWNER_PID" && "$OWNER_PID" == "$SERVER_PID" ]]; then
      rm -f "$LOCK_PATH"
    fi
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

step() { printf '\n=== %s ===\n' "$*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
step "1. Create fixture markdown"
# ---------------------------------------------------------------------------
cat > "$FIXTURE" <<'EOF'
# Smoke Test Doc

Hello, this is the first paragraph.

## Section A

- list item one
- list item two

```python
print("code block")
```

> A blockquote.

EOF

# ---------------------------------------------------------------------------
step "2. Spawn server"
# ---------------------------------------------------------------------------
python3 -m server.annotate_server "$FIXTURE" > "$LOG" 2>&1 &
SERVER_PID=$!

# ---------------------------------------------------------------------------
step "3. Wait for URL line"
# ---------------------------------------------------------------------------
URL=""
for _ in $(seq 1 100); do  # up to 10s in 100ms steps
  if grep -qE "^http://127[.]0[.]0[.]1:" "$LOG" 2>/dev/null; then
    URL="$(grep -Em1 "^http://127[.]0[.]0[.]1:" "$LOG")"
    break
  fi
  sleep 0.1
done
[[ -n "$URL" ]] || { cat "$LOG"; fail "server never printed URL"; }
PORT="${URL##*:}"
echo "URL=$URL  PORT=$PORT"

# ---------------------------------------------------------------------------
step "4. Health check"
# ---------------------------------------------------------------------------
HEALTH="$(curl -fsS "http://127.0.0.1:${PORT}/api/health")"
echo "$HEALTH" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["state"]=="ready", d; print("ready=OK")' \
  || fail "health did not report ready"

# ---------------------------------------------------------------------------
step "5. GET /api/document and pick first paragraph anchor"
# ---------------------------------------------------------------------------
DOC="$WORK/doc.json"
curl -fsS "http://127.0.0.1:${PORT}/api/document" > "$DOC"
ANCHOR_JSON="$(python3 -c "
import json,sys
d=json.load(open('$DOC'))
blocks=d['blocks']
assert len(blocks) >= 5, f'expected multiple blocks, got {len(blocks)}'
# Pick the first paragraph (kind == 'paragraph')
para = next(b for b in blocks if b['kind']=='paragraph')
print(json.dumps(para['anchor']))
")"
echo "anchor=$ANCHOR_JSON"

# ---------------------------------------------------------------------------
step "6. POST a comment"
# ---------------------------------------------------------------------------
COMMENT_BODY_JSON="$(python3 -c "
import json, sys
anchor = json.loads('''$ANCHOR_JSON''')
payload = {'anchor': anchor, 'body': 'smoke test comment'}
print(json.dumps(payload))
")"
RESP="$(curl -fsS -X POST -H 'Content-Type: application/json' \
  -d "$COMMENT_BODY_JSON" \
  "http://127.0.0.1:${PORT}/api/comments")"
echo "$RESP" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d["comment"]["body"]=="smoke test comment", d
print("posted=OK", d["comment"]["id"])
' || fail "POST /api/comments did not return the expected comment"

# ---------------------------------------------------------------------------
step "7. Sidecar file check"
# ---------------------------------------------------------------------------
[[ -f "$SIDECAR" ]] || fail "sidecar file not created"
python3 -c "
import json,sys
d=json.load(open('$SIDECAR'))
assert d['version']==1, d
assert len(d['comments'])==1, d
assert d['comments'][0]['body']=='smoke test comment', d
print('sidecar=OK')
" || fail "sidecar contents wrong"

# ---------------------------------------------------------------------------
step "8. POST /api/done"
# ---------------------------------------------------------------------------
DONE_RESP="$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/done")"
echo "$DONE_RESP" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d.get("ok") is True, d
assert d.get("orphans", []) == [], d
print("done=OK", "orphans=", d["orphans"])
' || fail "Done payload wrong"

# ---------------------------------------------------------------------------
step "9. Wait for server clean exit"
# ---------------------------------------------------------------------------
EXIT_CODE=0
for _ in $(seq 1 100); do  # up to 10s in 100ms steps
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    break
  fi
  sleep 0.1
done
if kill -0 "$SERVER_PID" 2>/dev/null; then
  cat "$LOG"
  fail "server did not exit after Done"
fi
wait "$SERVER_PID" || EXIT_CODE=$?
[[ "$EXIT_CODE" -eq 0 ]] || { cat "$LOG"; fail "server exit code $EXIT_CODE"; }
# Clear SERVER_PID so cleanup doesn't try to kill an already-gone process.
SERVER_PID=""
echo "server-exit=OK"

# ---------------------------------------------------------------------------
step "10. FR-32: no external URLs in static/"
# ---------------------------------------------------------------------------
STATIC_DIR="$PLUGIN_ROOT/server/static"
if [[ -d "$STATIC_DIR" ]]; then
  # Collect any http(s):// hits that are NOT 127.0.0.1
  EXTERNAL_URLS="$(grep -nrE "https?://" "$STATIC_DIR" | grep -vE "https?://127\\.0\\.0\\.1" || true)"
  if [[ -n "$EXTERNAL_URLS" ]]; then
    echo "$EXTERNAL_URLS" >&2
    fail "external URL in server/static/ — FR-32 violated"
  fi
  echo "fr32=OK"
else
  echo "fr32=SKIP (static/ directory not found)"
fi

# ---------------------------------------------------------------------------
step "11. apply-comments-prompt non-empty (if present from task 11)"
# ---------------------------------------------------------------------------
APPLY_TEMPLATE="$PLUGIN_ROOT/skills/annotate/references/apply-comments-prompt.md"
if [[ -f "$APPLY_TEMPLATE" ]]; then
  [[ -s "$APPLY_TEMPLATE" ]] || fail "apply-comments-prompt.md is empty"
  echo "apply-template=OK"
else
  echo "WARNING: apply-comments-prompt.md not yet present (task 11 not yet run) — skipping check"
fi

echo
echo "ALL E2E STEPS PASSED"
