"""โพสต์ขึ้น Facebook Page ผ่าน Graph API"""
from __future__ import annotations

import requests

TIMEOUT = 45


class FacebookError(RuntimeError):
    pass


class PageClient:
    def __init__(self, page_id: str, token: str, version: str = "v26.0"):
        self.page_id = page_id
        self.token = token
        self.base = f"https://graph.facebook.com/{version}"

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(
            f"{self.base}/{path}",
            data={**data, "access_token": self.token},
            timeout=TIMEOUT,
        )
        body = {}
        try:
            body = resp.json()
        except ValueError:
            pass
        if resp.status_code >= 400 or "error" in body:
            err = body.get("error", {})
            raise FacebookError(
                f"[{resp.status_code}] {err.get('type', '')} "
                f"code={err.get('code')} {err.get('message', resp.text[:300])}"
            )
        return body

    def whoami(self) -> dict:
        resp = requests.get(
            f"{self.base}/{self.page_id}",
            params={"fields": "id,name,fan_count", "access_token": self.token},
            timeout=TIMEOUT,
        )
        body = resp.json()
        if "error" in body:
            raise FacebookError(body["error"].get("message", "unknown"))
        return body

    def publish(self, message: str, link: str | None = None) -> str:
        data = {"message": message}
        if link:
            data["link"] = link
        return self._post(f"{self.page_id}/feed", data)["id"]

    def comment(self, post_id: str, message: str) -> str:
        return self._post(f"{post_id}/comments", {"message": message})["id"]
