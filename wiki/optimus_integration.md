# Optimus Integration

## Overview
SAM creates homepage widgets on ApnaMart app via Optimus API.
Replaces manual Maker (Manoj) workflow.

## Credentials
- **Username:** Automation
- **Password:** Qwerty@123
- **API Base:** `https://optimus-app-hazel.vercel.app/api/local`
- **Role:** To be configured (Maker or SUPER_ADMIN for auto-approve)

## Widget Types

### 1. SPR (Single/Double Product Row)
Most common widget. Shows products in a horizontal row.

| Variant | PNC Config |
|---------|-----------|
| Single Row | `rows: 1, optimized: false` |
| Single Row V2 (Optimized) | `rows: 1, optimized: true` |
| Double Row | `rows: 2, optimized: false` |
| Double Row V2 (Optimized) | `rows: 2, optimized: true` |
| Multimedia SPR | `rows: 1, has_multimedia: true` |

**Required:** slug, title, stateProducts (global + optional state overrides)

**Voice Command:** "Rice sale ka SPR banao, products 101, 102, 103"
**Tag:** `[CREATE_SPR: Rice Sale | 101,102,103 | 1 | true]`

### 2. Collection Banner
Carousel or category grid on homepage.

| Mode | Description |
|------|-------------|
| `scroll` | Horizontal carousel of banners |
| `stick` | Sticky category grid |

**Voice Command:** "Summer collection ka banner banao"
**Tag:** `[CREATE_BANNER: Summer Collection | scroll]`

### 3. Masthead
Header widget at top of homepage.

| Variant | Description |
|---------|-------------|
| `primary` | Simple single masthead |
| `secondary` | Complex with carousel items |

**Voice Command:** "Diwali ka masthead lagao"
**Tag:** `[CREATE_MASTHEAD: diwali_masthead | primary]`

---

## API Flow

```
1. POST /requests (with widgets array)
   → If SUPER_ADMIN: auto-approved
   → If Maker: status = PENDING (needs checker approval)

2. POST /requests/:id/approve (checker only)

3. Deploy via BackendSyncService
   → Creates sub-category items
   → Creates PLP widget
   → Creates page layout
   → Maps everything via CSV
```

## State Products
Products can be state-specific:
- `global` — all states (required)
- `jh` — Jharkhand override
- `cg` — Chhattisgarh override
- `wb` — West Bengal override
- `patna` — City override

## Slug Naming
Format: `{title_snake_case}_{timestamp}`
Suffixes auto-added by backend: `_spr`, `_spr_opt`, `_cl_w_hp`, `_pm_hp`

## Open Questions
1. Item codes: manual se milenge ya catalog API se auto-search?
2. Slug naming convention: decide karna hai
3. Automation account role: Maker ya SUPER_ADMIN?

## Files
- `optimus_agent.py` — API client for widget CRUD
- `configs/optimus_config.json` — Credentials + widget type config
