"""Client for the Google Apps Script web app (apps_script/Code.gs) that logs leads to the Sheet."""
import json

import requests

from insider.util import redact

USER_AGENT = "InsiderJobPipeline/1.0 (+https://github.com/zshqv/Insider)"
EXPECTED_SCRIPT_VERSION = 3
BATCH_SIZE = 25

HINT_HTML = (
    "Apps Script returned an HTML page instead of JSON. The deployment is almost certainly not public: "
    "in the Apps Script editor go to Deploy > Manage deployments > Edit and set "
    "'Execute as: Me' and 'Who has access: Anyone', then deploy a New version."
)
HINT_OLD_SCRIPT = (
    "Apps Script answered with the OLD script (plain-text 'Success' or no version). "
    "Paste apps_script/Code.gs into the editor, then Deploy > Manage deployments > Edit > "
    "Version: New version > Deploy."
)


class SheetError(Exception):
    pass


class SheetClient:
    def __init__(self, url, session=None, timeout=120):
        self.url = url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def health(self):
        """GET the web app: returns version, tab name and headers. Raises SheetError on any problem."""
        return self._request("GET")

    def append(self, leads):
        """Append leads (list of dicts). Returns one result dict per lead:
        {"status": "ok" | "duplicate" | "error", ...}. Raises SheetError if the whole call fails."""
        results = []
        for i in range(0, len(leads), BATCH_SIZE):
            batch = leads[i:i + BATCH_SIZE]
            data = self._request("POST", {"leads": batch})
            batch_results = data.get("results")
            if isinstance(batch_results, list) and len(batch_results) == len(batch):
                results.extend(batch_results)
            elif data.get("status") == "ok" and "data_rows" in data:
                results.extend([{"status": "ok"}] * len(batch))
            else:
                raise SheetError(f"Unexpected response shape: {json.dumps(data)[:300]}")
        return results

    def _request(self, method, payload=None):
        try:
            # Apps Script answers POST /exec with a 302 to googleusercontent.com;
            # requests follows it as a GET, which is how the script's output is fetched.
            if method == "POST":
                res = self.session.post(
                    self.url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "text/plain"},
                    timeout=self.timeout,
                )
            else:
                res = self.session.get(self.url, timeout=self.timeout)
        except requests.RequestException as e:
            raise SheetError(f"HTTP request failed: {redact(e, self.url)}") from None

        body = res.text.strip()
        if res.status_code != 200:
            raise SheetError(f"HTTP {res.status_code}: {redact(body[:300], self.url)}")
        if body.startswith("<") or "text/html" in res.headers.get("Content-Type", ""):
            raise SheetError(HINT_HTML)
        if body == "Success" or body.startswith("No valid payload") or body.startswith("Error:"):
            raise SheetError(f"{HINT_OLD_SCRIPT} (response: {body[:200]!r})")
        try:
            data = json.loads(body)
        except ValueError:
            raise SheetError(f"Response is not JSON: {redact(body[:300], self.url)}") from None

        if data.get("status") != "ok":
            raise SheetError(f"Apps Script error: {data.get('message', data)}")
        version = data.get("version")
        if version is None or version < EXPECTED_SCRIPT_VERSION:
            raise SheetError(f"{HINT_OLD_SCRIPT} (live version: {version}, expected {EXPECTED_SCRIPT_VERSION})")
        return data
