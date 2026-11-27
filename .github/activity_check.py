"""Daily quiet-app check for am.go (run by .github/workflows/keep-counter.yml).

Reads the daily counters the app keeps (visits-YYYY-MM-DD, prints-YYYY-MM-DD, UTC days) and works out how many
days it has been since anyone opened the app or printed. After QUIET_DAYS with nothing, it opens one GitHub issue
that mentions @clrayos; once there's activity again it closes that issue. Only numbers are involved.
"""
import datetime as dt, json, subprocess, time, urllib.request, urllib.error

NS = "archivedmoments-go"
START = dt.date(2026, 11, 28)      # daily counters exist from this day on
QUIET_DAYS = 14
LOOKBACK = 60
TITLE = "am.go has been quiet"

def get(key):
    url = f"https://abacus.jasoncameron.dev/get/{NS}/{key}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "am.go-keepalive"}), timeout=15) as r:
                return int(json.load(r).get("value") or 0)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0
            time.sleep(3)
        except Exception:
            time.sleep(3)
    raise RuntimeError(f"could not read {key}")

def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout

today = dt.datetime.now(dt.timezone.utc).date()
quiet = None
for i in range(LOOKBACK):
    d = today - dt.timedelta(days=i)
    if d < START:
        break
    k = d.isoformat()
    v, p = get("visits-" + k), get("prints-" + k)
    time.sleep(0.5)
    if i == 0:
        print(f"today ({k}): {v} visits, {p} prints")
    if v or p:
        quiet = i
        print(f"last activity: {k} ({v} visits, {p} prints) -> {i} quiet day(s)")
        break
if quiet is None:
    quiet = min((today - START).days, LOOKBACK)
    print(f"no activity found since {START} -> {quiet} quiet day(s)")

open_issues = json.loads(gh("issue", "list", "--state", "open", "--search", f'"{TITLE}" in:title', "--json", "number,title"))
mine = [i for i in open_issues if i["title"].startswith(TITLE)]

if quiet >= QUIET_DAYS and not mine:
    body = (f"@clrayos nobody has opened or printed with am.go for **{quiet} days**.\n\n"
            "Nothing is broken and nothing has been switched off: the counters are kept alive every day by this job. "
            "This is just a heads-up in case you'd like to share the link again: https://amphotobooth.com/go\n\n"
            "This issue closes by itself as soon as someone uses the app.")
    gh("issue", "create", "--title", f"{TITLE} for {quiet} days", "--body", body)
    print("opened a quiet-app issue")
elif quiet < QUIET_DAYS and mine:
    for i in mine:
        gh("issue", "close", str(i["number"]), "--comment", f"Someone used am.go again ({quiet} day(s) ago), so it's active again. Closing this.")
    print("activity is back: closed the quiet-app issue")
else:
    print("nothing to do")
