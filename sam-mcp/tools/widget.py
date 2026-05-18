"""
sam_widget — Widget operations: create, edit, list, get, duplicate, history.
All data reads/writes go to BigQuery (apna-mart-data.optimus.*).
Widget deployment to backend goes via Samaan API.
"""


async def handle_widget(arguments: dict, configs: dict) -> dict:
    """Route widget actions to handlers."""
    action = arguments.get("action")

    if not action:
        return {"error": "widget requires 'action' parameter. Options: create, edit, list, get, duplicate, history"}

    if action == "create":
        return await _create(arguments, configs)
    elif action == "edit":
        return await _edit(arguments, configs)
    elif action == "list":
        return await _list(arguments, configs)
    elif action == "get":
        return await _get(arguments, configs)
    elif action == "duplicate":
        return await _duplicate(arguments, configs)
    elif action == "history":
        return await _history(arguments, configs)
    else:
        return {"error": f"widget.{action} is not a valid action. Options: create, edit, list, get, duplicate, history"}


async def _create(args: dict, configs: dict) -> dict:
    """Create a new widget. Validates required fields, asks for missing ones."""
    missing = []

    widget_type = args.get("type")  # spr, dpr, banner_scroll, banner_stick, primary_masthead, secondary_masthead
    title = args.get("title")
    states = args.get("states")
    products = args.get("products")
    start_time = args.get("start_time")
    end_time = args.get("end_time")
    page_type = args.get("page_type")
    image = args.get("image")
    slug = args.get("slug")
    env = args.get("env")
    rows = args.get("rows", 2 if widget_type == "dpr" else 1)  # 1=single, 2=double
    is_optimized = args.get("is_optimized", True)  # default optimized

    # Environment is FIRST question
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    # Check required fields
    if not widget_type:
        missing.append("type — Which widget? Options: spr, banner_scroll, banner_stick, primary_masthead, secondary_masthead")
    if not title:
        missing.append("title — Widget title?")
    if not states:
        missing.append("states — Which states? e.g. ['JH', 'CG', 'WB']")
    if not start_time:
        missing.append("start_time — Start date? (YYYY-MM-DD HH:MM:SS)")
    if not end_time:
        missing.append("end_time — End date? (YYYY-MM-DD HH:MM:SS)")

    # Type-specific required fields
    if widget_type in ("spr", "banner_scroll", "banner_stick") and not products:
        missing.append("products — Product codes? (comma-separated or Sheet URL)")
    if widget_type in ("banner_scroll", "banner_stick", "primary_masthead", "secondary_masthead") and not image:
        missing.append("image — Image URL?")
    if widget_type in ("spr", "banner_scroll", "banner_stick") and not page_type:
        missing.append("page_type — Product Listing Page or Category Page?")

    if missing:
        return {"status": "missing_fields", "message": "Please provide the following details:", "missing": missing}

    confirm = args.get("confirm", False)
    final_slug = slug or _generate_slug(title, widget_type)

    # If confirm=false → show summary
    if not confirm:
        return {
            "status": "ready",
            "message": f"Ready to create on {env}. Call again with confirm=true to execute.",
            "environment": env,
            "summary": {
                "type": widget_type, "title": title, "slug": final_slug,
                "states": states, "products": products, "page_type": page_type,
                "image": image, "start_time": start_time, "end_time": end_time,
            },
            "next_step": "Show this summary to user. If user confirms, call sam_widget again with all same params + confirm=true"
        }

    # confirm=true → DEPLOY via Samaan API
    from clients.samaan_client import SamaanClient
    from logger.bq_logger import log_action, log_slug_event

    samaan_cfg = configs.get("samaan", {})
    samaan = SamaanClient(samaan_cfg, env)

    # Login to Samaan
    login_ok = await samaan.login()
    if not login_ok:
        return {"status": "failed", "error": f"Samaan login failed on {env}. Check credentials."}

    product_list = [p.strip() for p in products.split(",") if p.strip()]

    # Deploy based on widget type
    if widget_type in ("spr", "dpr"):
        from clients.spr_deployer import deploy_spr

        deploy_data = {
            "slug": final_slug,
            "title": title,
            "titleHi": "",
            "products": products,
            "stateProducts": _build_state_products(states, products),
            "pageType": page_type,
            "start_time": start_time,
            "end_time": end_time,
            "rows": rows,
            "is_optimized": is_optimized,
            "has_multimedia": bool(image),
            "image": image,
        }

        result = await deploy_spr(samaan, deploy_data)
    elif widget_type == "banner_scroll":
        from clients.banner_carousel_deployer import deploy_banner_carousel

        deploy_data = {
            "slug": final_slug,
            "title": title,
            "products": products,
            "stateProducts": _build_state_products(states, products),
            "image": image,
            "media_number": args.get("media_number", "3.5"),
            "start_time": start_time,
            "end_time": end_time,
        }

        result = await deploy_banner_carousel(samaan, deploy_data)
    elif widget_type == "banner_stick":
        from clients.banner_stick_deployer import deploy_banner_stick

        deploy_data = {
            "slug": final_slug,
            "title": title,
            "products": products,
            "stateProducts": _build_state_products(states, products),
            "image": image,
            "start_time": start_time,
            "end_time": end_time,
        }

        result = await deploy_banner_stick(samaan, deploy_data)
    elif widget_type == "primary_masthead":
        from clients.masthead_deployer import deploy_primary_masthead

        deploy_data = {
            "slug": final_slug,
            "master_key": args.get("master_key", ""),
            "image": image,
            "start_time": start_time,
            "end_time": end_time,
            "aspect_ratio": args.get("aspect_ratio", "1"),
        }
        result = await deploy_primary_masthead(samaan, deploy_data)
    elif widget_type == "secondary_masthead":
        from clients.masthead_deployer import deploy_secondary_masthead

        deploy_data = {
            "slug": final_slug,
            "image": image,
            "master_key": args.get("master_key", ""),
            "carousel_items": args.get("carousel_items", []),
            "start_time": start_time,
            "end_time": end_time,
            "aspect_ratio": args.get("aspect_ratio", "4"),
        }
        result = await deploy_secondary_masthead(samaan, deploy_data)
    else:
        result = {"status": "failed", "message": f"Unknown widget type: {widget_type}"}

    await samaan.close()

    if result.get("status") == "deployed":
        log_action("sam_mcp", "widget.create", final_slug, {"type": widget_type, "env": env}, result, "success")
        log_slug_event(final_slug, "created", "sam_mcp", {"type": widget_type, "states": states})
        return {
            "status": "deployed",
            "message": f"Widget deployed on {env}!",
            "environment": env,
            "widget_slug": result.get("spr_slug") or result.get("carousel_slug") or result.get("category_slug") or result.get("masthead_slug") or final_slug,
            "spr_slug": result.get("spr_slug"),
            "carousel_slug": result.get("carousel_slug"),
            "category_slug": result.get("category_slug"),
            "plp_slug": result.get("plp_slug"),
            "page_slug": result.get("page_slug"),
            "title": title,
            "states": states,
            "products_count": len(product_list),
            "steps": result.get("steps", []),
        }
    else:
        log_action("sam_mcp", "widget.create", final_slug, {"type": widget_type, "env": env}, result, "failed", str(result.get("error", "")))
        return {
            "status": "failed",
            "message": f"Widget deploy failed on {env}.",
            "environment": env,
            "slug": final_slug,
            "error": result.get("error", "Unknown error"),
            "steps_completed": [s for s in result.get("steps", []) if s.get("status") == "ok"],
        }


async def _edit(args: dict, configs: dict) -> dict:
    """Edit existing widget by slug."""
    env = args.get("env")
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    slug = args.get("slug")
    fields = args.get("fields_to_update")

    if not slug:
        return {"error": "widget.edit requires 'slug' parameter."}
    if not fields:
        return {"error": "widget.edit requires 'fields_to_update' parameter. What do you want to change?"}

    from clients.bq_client import BQClient
    bq = BQClient()

    # Verify widget exists
    widget = bq.get_widget(slug, env)
    if "error" in widget:
        return widget

    return {
        "status": "pending_implementation",
        "message": f"Widget '{slug}' found on {env}. Edit via BQ update coming soon.",
        "environment": env,
        "slug": slug,
        "current_widget": {k: str(v)[:100] for k, v in widget.items() if k in ("type", "title", "status", "products")},
        "updates": fields
    }


async def _list(args: dict, configs: dict) -> dict:
    """List widgets from BigQuery."""
    env = args.get("env")
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    from clients.bq_client import BQClient
    bq = BQClient()

    filters = {}
    if args.get("type"):
        filters["type"] = args["type"]
    if args.get("status"):
        filters["status"] = args["status"]
    if args.get("slug"):
        filters["slug"] = args["slug"]

    widgets = bq.list_widgets(env, filters)
    return {
        "environment": env,
        "count": len(widgets),
        "widgets": [{
            "slug": w.get("slug"),
            "type": w.get("type"),
            "title": w.get("title"),
            "status": w.get("status"),
            "created_at": str(w.get("created_at", "")),
        } for w in widgets]
    }


async def _get(args: dict, configs: dict) -> dict:
    """Get widget details from BigQuery."""
    env = args.get("env")
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    slug_or_id = args.get("slug_or_id")
    if not slug_or_id:
        return {"error": "widget.get requires 'slug_or_id' parameter."}

    from clients.bq_client import BQClient
    bq = BQClient()

    widget = bq.get_widget(slug_or_id, env)
    if "error" in widget:
        return widget

    # Convert non-serializable fields
    result = {}
    for k, v in widget.items():
        result[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v

    result["environment"] = env
    return result


async def _duplicate(args: dict, configs: dict) -> dict:
    """Duplicate existing widget."""
    env = args.get("env")
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    slug = args.get("slug")
    if not slug:
        return {"error": "widget.duplicate requires 'slug' parameter."}

    from clients.bq_client import BQClient
    bq = BQClient()

    widget = bq.get_widget(slug, env)
    if "error" in widget:
        return widget

    return {
        "status": "pending_implementation",
        "message": f"Widget '{slug}' found on {env}. Duplicate via BQ insert coming soon.",
        "environment": env,
        "original_slug": slug,
    }


async def _history(args: dict, configs: dict) -> dict:
    """View slug lifecycle from widget_versions table."""
    env = args.get("env")
    if not env:
        return {"status": "missing_env", "message": "Which environment? PROD or UAT?", "options": ["PROD", "UAT"]}

    slug = args.get("slug")
    if not slug:
        return {"error": "widget.history requires 'slug' parameter."}

    from clients.bq_client import BQClient
    bq = BQClient()

    versions = bq.get_versions(slug, env)
    return {
        "environment": env,
        "slug": slug,
        "versions_count": len(versions),
        "versions": [{
            "version": v.get("version"),
            "changed_by": v.get("changed_by"),
            "change_log": v.get("change_log"),
            "created_at": str(v.get("created_at", "")),
        } for v in versions]
    }


def _build_pnc(widget_type: str, image: str = None) -> dict:
    """Build PNC based on widget type."""
    if widget_type == "spr":
        return {"rows": 1, "is_optimized": True, "has_multimedia": bool(image)}
    elif widget_type == "banner_scroll":
        return {"displayMode": "scroll"}
    elif widget_type == "banner_stick":
        return {"displayMode": "stick"}
    elif widget_type == "primary_masthead":
        return {"variant": "primary", "has_multimedia": bool(image)}
    elif widget_type == "secondary_masthead":
        return {"variant": "secondary", "has_multimedia": bool(image)}
    return {}


def _build_state_products(states: list, products: str) -> dict:
    """Build state-wise products dict."""
    result = {"global": products}
    state_map = {
        "JH": "jharkhand", "CG": "chhattisgarh", "WB": "west bengal",
        "UP": "uttar pradesh", "PATNA": "patna"
    }
    for state in (states or []):
        key = state.upper()
        if key in state_map:
            result[state_map[key]] = products
    return result


def _generate_slug(title: str, widget_type: str) -> str:
    """Generate slug from title + widget type."""
    base = title.lower().replace(" ", "_").replace("-", "_")
    base = "".join(c for c in base if c.isalnum() or c == "_")
    base = base[:50]

    type_suffix = {
        "spr": "_spr_opt",
        "banner_scroll": "_Cl_w_HP",
        "banner_stick": "_cm_hp",
        "primary_masthead": "_pm_hp",
        "secondary_masthead": "_sm_hp",
    }
    return f"{base}{type_suffix.get(widget_type, '')}"
