"""
Samaan API Client — handles auth (auto-login) + all 8 Samaan API calls.
Auto re-login on 403 session expiry.
"""

import aiohttp
import asyncio


class SamaanClient:
    def __init__(self, config: dict, env: str = None):
        self.env = env or config.get("default_env", "UAT")
        self.base_url = config.get("environments", {}).get(self.env, config.get("environments", {}).get("UAT", ""))
        creds = config["credentials"].get(self.env, config["credentials"].get("UAT", {}))
        self.username = creds["username"]
        self.password = creds["password"]
        self.endpoints = config["endpoints"]
        self.csrf_token = None
        self.session_id = None
        self._session = None

    async def _ensure_session(self):
        """Create aiohttp session with cookie jar for auto cookie handling."""
        if self._session is None or self._session.closed:
            jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(cookie_jar=jar)

    async def login(self) -> bool:
        """Auto-login to Samaan. Returns True on success."""
        await self._ensure_session()

        # Step 1: GET /login/ to get csrftoken
        login_url = f"{self.base_url}{self.endpoints['login']}"
        async with self._session.get(login_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            cookies = resp.cookies
            self.csrf_token = None
            for cookie in cookies.values():
                if cookie.key == "csrftoken":
                    self.csrf_token = cookie.value
                    break

        if not self.csrf_token:
            return False

        # Step 2: POST /login/ with credentials
        data = aiohttp.FormData()
        data.add_field("csrfmiddlewaretoken", self.csrf_token)
        data.add_field("username", self.username)
        data.add_field("password", self.password)

        headers = {
            "Cookie": f"csrftoken={self.csrf_token}",
            "Referer": login_url,
        }

        async with self._session.post(
            login_url, data=data, headers=headers,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            cookies = resp.cookies
            for cookie in cookies.values():
                if cookie.key == "sessionid":
                    self.session_id = cookie.value
                    break

        return self.session_id is not None

    def _auth_headers(self) -> dict:
        """Build auth headers with CSRF + session cookies."""
        return {
            "X-CSRFToken": self.csrf_token or "",
            "Cookie": f"csrftoken={self.csrf_token}; sessionid={self.session_id}",
        }

    async def _request(self, method: str, endpoint_key: str, data=None, json_body=None, is_retry=False) -> dict:
        """Make authenticated request. Auto re-login on 403."""
        await self._ensure_session()

        if not self.session_id:
            success = await self.login()
            if not success:
                return {"error": "Samaan login failed. Check credentials."}

        url = f"{self.base_url}{self.endpoints[endpoint_key]}"
        headers = self._auth_headers()

        try:
            async with self._session.request(
                method, url,
                headers=headers,
                data=data,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 403 and not is_retry:
                    # Session expired — re-login and retry
                    success = await self.login()
                    if success:
                        return await self._request(method, endpoint_key, data=data, json_body=json_body, is_retry=True)
                    return {"error": "Samaan session expired. Re-login failed."}

                try:
                    result = await resp.json()
                except:
                    result = {"raw": await resp.text()}

                if resp.status >= 400:
                    return {
                        "error": f"Samaan API {method} {endpoint_key} failed: HTTP {resp.status}",
                        "detail": result
                    }
                return result

        except Exception as e:
            return {"error": f"Samaan API {method} {endpoint_key} failed: {str(e)}"}

    # ── Widget Item ──

    async def create_widget_item(self, form_data: aiohttp.FormData) -> dict:
        """POST /api/app/post_widget_item/ — multipart form."""
        return await self._post_form("widget_item", form_data)

    # ── Widget ──

    async def create_widget(self, form_data: aiohttp.FormData) -> dict:
        """POST /api/app/widget/ — multipart form."""
        return await self._post_form("widget", form_data)

    async def _post_form(self, endpoint_key: str, form_data: aiohttp.FormData, is_retry=False) -> dict:
        """Post multipart form with auth. CSRF token in both header AND body."""
        await self._ensure_session()
        if not self.session_id:
            success = await self.login()
            if not success:
                return {"error": "Samaan login failed."}

        # Django needs csrfmiddlewaretoken in form body + X-CSRFToken header + Cookie
        form_data.add_field("csrfmiddlewaretoken", self.csrf_token or "")

        url = f"{self.base_url}{self.endpoints[endpoint_key]}"
        headers = {
            "X-CSRFToken": self.csrf_token or "",
            "Cookie": f"csrftoken={self.csrf_token}; sessionid={self.session_id}",
            "Referer": self.base_url,
        }

        try:
            async with self._session.post(url, data=form_data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 403 and not is_retry:
                    success = await self.login()
                    if success:
                        return await self._post_form(endpoint_key, form_data, is_retry=True)
                    return {"error": "Session expired. Re-login failed."}
                try:
                    return await resp.json()
                except:
                    text = await resp.text()
                    if resp.status >= 400:
                        return {"error": f"HTTP {resp.status}", "raw": text[:500]}
                    return {"status": resp.status, "raw": text[:500]}
        except Exception as e:
            return {"error": str(e)}

    # ── Page Layout ──

    async def create_page_layout(self, json_body: dict) -> dict:
        """POST /api/app/post_page_layout/ — JSON."""
        return await self._request("POST", "page_layout", json_body=json_body)

    # ── Multimedia ──

    async def upload_multimedia(self, form_data: aiohttp.FormData) -> dict:
        """POST /api/app/multimedia/ — multipart form."""
        return await self._post_form("multimedia", form_data)

    # ── Mapping (CSV upload) ──

    async def map_widget_items(self, csv_blob: bytes, filename: str = "mapping.csv") -> dict:
        """POST /api/app/update_widget_widget_item_mapping/ — CSV file upload."""
        return await self._post_mapping("map_widget_items", csv_blob, filename)

    async def map_widget_items_with_slug(self, widget_slug: str, csv_blob: bytes) -> dict:
        """Map widget items with widget_slug in form body (as GAS script does)."""
        form = aiohttp.FormData()
        form.add_field("widget_slug", widget_slug)
        form.add_field("mapping_file", csv_blob, filename="map.csv", content_type="text/csv")
        return await self._post_form("map_widget_items", form)

    async def map_layout_widget(self, csv_blob: bytes, filename: str = "mapping.csv") -> dict:
        """POST /api/app/update_layout_widget_mapping/ — CSV file upload."""
        return await self._post_mapping("map_layout_widget", csv_blob, filename)

    async def map_layout_widget_with_slug(self, page_layout_slug: str, csv_blob: bytes) -> dict:
        """Map layout widget with page_layout_slug in form body."""
        form = aiohttp.FormData()
        form.add_field("page_layout_slug", page_layout_slug)
        form.add_field("mapping_file", csv_blob, filename="map.csv", content_type="text/csv")
        return await self._post_form("map_layout_widget", form)

    async def map_page_layout(self, csv_blob: bytes, filename: str = "mapping.csv") -> dict:
        """POST /api/app/update_page_page_layout_mapping/ — CSV file upload."""
        return await self._post_mapping("map_page_layout", csv_blob, filename)

    async def map_page_layout_with_slug(self, page_layout_slug: str, page_type: str, csv_blob: bytes) -> dict:
        """Map page layout with page_layout_slug + page_type in form body."""
        form = aiohttp.FormData()
        form.add_field("page_layout_slug", page_layout_slug)
        form.add_field("page_type", page_type)
        form.add_field("mapping_file", csv_blob, filename="map.csv", content_type="text/csv")
        return await self._post_form("map_page_layout", form)

    async def _post_mapping(self, endpoint_key: str, csv_blob: bytes, filename: str) -> dict:
        """Post mapping CSV."""
        form = aiohttp.FormData()
        form.add_field("mapping_file", csv_blob, filename=filename, content_type="text/csv")
        return await self._post_form(endpoint_key, form)

    # ── Bulk Upload ──

    async def bulk_upload(self, csv_blob: bytes, filename: str = "bulk_upload.csv") -> dict:
        """PUT /api/app/bulk_upload_products_for_wi/ — CSV file upload."""
        await self._ensure_session()
        if not self.session_id:
            await self.login()

        url = f"{self.base_url}{self.endpoints['bulk_upload']}"
        headers = {"X-CSRFToken": self.csrf_token or "", "Referer": self.base_url}

        form = aiohttp.FormData()
        form.add_field("file", csv_blob, filename=filename, content_type="text/csv")

        async with self._session.put(url, data=form, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            try:
                return await resp.json()
            except:
                return {"status": resp.status, "raw": await resp.text()}

    # ── Cleanup ──

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
