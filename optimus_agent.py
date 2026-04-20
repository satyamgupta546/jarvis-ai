"""Optimus Agent - Create, approve, and deploy widgets via API.
Satyam = SUPER_ADMIN → auto-approve on submit.
"""

import json
import urllib.request
import urllib.parse

# ── Optimus Config ──
OPTIMUS_API = "https://optimus-app-hazel.vercel.app/api/local"
OPTIMUS_USER = "satyam.gupta@apnamart.in"  # SUPER_ADMIN
OPTIMUS_ENV = "PROD"


def _api(method: str, endpoint: str, body: dict = None) -> dict:
    """Call Optimus API."""
    url = f"{OPTIMUS_API}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-Optimus-User": OPTIMUS_USER,
        "X-Optimus-Env": OPTIMUS_ENV,
    }

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {error_body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════
# Widget Creation
# ══════════════════════════════════════

def create_spr_widget(
    slug: str,
    title: str,
    products_global: str,
    products_jh: str = "",
    products_cg: str = "",
    products_wb: str = "",
    rows: int = 1,
    optimized: bool = True,
    title_hi: str = "",
) -> dict:
    """Create a Single/Double Product Rail widget.

    Args:
        slug: Unique slug (e.g. 'rice_sale_2026')
        title: English title
        products_global: Comma-separated item codes for all states
        products_jh/cg/wb: State-specific overrides (optional)
        rows: 1 = single row, 2 = double row
        optimized: True = v2 (better performance)
        title_hi: Hindi title (optional)
    """
    state_products = {"global": products_global}
    if products_jh:
        state_products["jh"] = products_jh
    if products_cg:
        state_products["cg"] = products_cg
    if products_wb:
        state_products["wb"] = products_wb

    widget = {
        "type": "product_rail",
        "slug": slug,
        "title": title,
        "titleHi": title_hi or title,
        "pnc": {"rows": rows, "is_optimized": optimized, "has_multimedia": False},
        "stateProducts": state_products,
        "config": {},
        "products": [],
        "sortOrder": 0,
    }

    # Step 1: Submit (auto-approves for SUPER_ADMIN)
    result = _api("POST", "/requests", {
        "widgets": [widget],
        "headerWidgets": {},
    })

    if "error" in result:
        return {"status": "error", "error": result["error"]}

    return {
        "status": "ok",
        "message": f"SPR widget '{title}' created and auto-approved!",
        "request_id": result.get("id"),
        "request_status": result.get("status"),
        "widget_slug": slug,
    }


def create_collection_banner(
    slug: str,
    title: str,
    display_mode: str = "scroll",
    items: list[dict] = None,
) -> dict:
    """Create a Collection Banner widget.

    Args:
        slug: Unique slug
        title: Banner title
        display_mode: 'scroll' (carousel) or 'stick' (category grid)
        items: List of banner items with 'pageHeading', 'image', 'stateProducts'
    """
    widget = {
        "type": "collection_banner",
        "slug": slug,
        "title": title,
        "displayMode": display_mode,
        "scrollItems": items or [],
        "config": {},
        "products": [],
        "sortOrder": 0,
    }

    result = _api("POST", "/requests", {
        "widgets": [widget],
        "headerWidgets": {},
    })

    if "error" in result:
        return {"status": "error", "error": result["error"]}

    return {
        "status": "ok",
        "message": f"Collection Banner '{title}' created!",
        "request_id": result.get("id"),
    }


def create_masthead(
    slug: str,
    variant: str = "primary",
    carousel_items: list[dict] = None,
) -> dict:
    """Create a Masthead widget.

    Args:
        slug: Unique slug
        variant: 'primary' or 'secondary'
        carousel_items: For secondary — list of items with pageHeading, image, subCategories
    """
    config = {}
    if variant == "secondary" and carousel_items:
        config["carouselItems"] = carousel_items

    widget = {
        "type": "masthead",
        "slug": slug,
        "variant": variant,
        "config": config,
        "products": [],
        "sortOrder": 0,
    }

    result = _api("POST", "/requests", {
        "widgets": [widget],
        "headerWidgets": {f"{'primaryMasthead' if variant == 'primary' else 'secondaryMasthead'}": config},
    })

    if "error" in result:
        return {"status": "error", "error": result["error"]}

    return {
        "status": "ok",
        "message": f"Masthead ({variant}) created!",
        "request_id": result.get("id"),
    }


# ══════════════════════════════════════
# Widget Management
# ══════════════════════════════════════

def list_widgets(env: str = "PROD") -> dict:
    """List all widgets."""
    return _api("GET", f"/widgets?env={env}")


def get_widget(widget_id: str) -> dict:
    """Get widget details."""
    return _api("GET", f"/widgets/{widget_id}")


def list_requests(status: str = "") -> dict:
    """List approval requests. status: PENDING, APPROVED, REJECTED"""
    endpoint = "/requests"
    if status:
        endpoint += f"?status={status}"
    return _api("GET", endpoint)


def deploy_request(request_id: str) -> dict:
    """Deploy an approved request to production."""
    return _api("POST", f"/requests/{request_id}/deploy")


# ══════════════════════════════════════
# Quick Actions (Jarvis-friendly)
# ══════════════════════════════════════

def quick_create_spr(title: str, product_codes: str) -> dict:
    """Quickest way to create an SPR widget.
    title: 'Rice Sale'
    product_codes: '101,102,103'
    """
    slug = title.lower().replace(" ", "_").replace("-", "_")
    # Add timestamp to avoid slug conflict
    import time
    slug = f"{slug}_{int(time.time()) % 100000}"
    return create_spr_widget(slug=slug, title=title, products_global=product_codes)


# Test
if __name__ == "__main__":
    print("Testing Optimus API connection...")
    result = list_widgets()
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        widgets = result if isinstance(result, list) else result.get("widgets", [])
        print(f"Connected! {len(widgets)} widgets found.")
