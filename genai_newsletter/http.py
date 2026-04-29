from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(slots=True)
class HttpClient:
    timeout: int = 20
    user_agent: str = "genai-newsletter/0.1 (+https://local.dev)"

    def get_text(self, url: str, params: dict[str, str | int] | None = None) -> str:
        if params:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"GET failed for {url}: {exc}") from exc

    def get_json(self, url: str, params: dict[str, str | int] | None = None) -> dict:
        return json.loads(self.get_text(url, params=params))
