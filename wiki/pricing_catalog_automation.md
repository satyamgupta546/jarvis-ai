# Pricing & Catalog Automation — SAM

## Overview
SAM will monitor 2 Slack channels and auto-fix pricing/catalog issues via samaan API.

## Channels to Monitor

### 1. #pricing-feedback (C04QS6GT11R)
**Request types:**
- MRP update — "item code 661, update mrp"
- EAN update — "item code 28101, map EAN"

**Requesters:** Elizabeth Kujur, Suraj Pandey, Beauty Kumari
**Currently handled by:** Azeem Namaji

### 2. #catalogue-grn-escalations (C08DJ3FEUN7) — Private
**Request types:**
- EAN Mapping (~60%) — "Item code 3818, EAN mapping update"
- Product Code Mapping (~25%) — "Map product code 67185"
- GST/HSN Update (~10%) — "Item 46558, GST 5%, HSN 18069010"
- Other (~5%) — grammage update, image update

**Requesters:** Viraj Kumar, Penaki, Lokesh Yadav, Gautam Kumar Mahto, Beauty Kumari, Mahesh Yadav
**Currently handled by:** Azeem (U07NC3G5RRC), Sravan (U09BDR7JWTV), Subham Sen (U084SCCBW9X)

## Trigger
- Koi bhi @SAM ya @Azeem Namaji ko tag kare
- Message mein item code + action ho

## Flow
```
1. Slack message aaye (mention @SAM or @Azeem)
2. SAM extract kare:
   - Item code (number)
   - Action type (EAN mapping / MRP update / GST update / Product mapping)
   - Extra data if any (MRP value, GST %, HSN code, warehouse)
3. samaan API call kare — fix kare
4. Thread mein reply kare: "Done ✅ — SAM"
5. If validation needed (image etc.) — ask in thread, wait for reply, then process
```

## Tech
- Language: Python
- Slack: Bot token (xoxb-...) + Event Subscriptions (real-time)
- API: samaan.apnamart.in (endpoints TBD — Satyam will provide)
- Location: sam_agent.py ya alag script

## Pending
- [ ] samaan API endpoints for MRP update, EAN mapping, GST update, product mapping
- [ ] Slack Event Subscriptions setup (after script is ready)
- [ ] Testing with real data

## Rules
- SAM reply karega thread mein — main channel mein nahi
- Har action logged hoga conversations.json mein
- Agar kuch samajh na aaye → ask in thread, don't guess
- Agar API fail ho → reply "Unable to process, please check manually"
- Jab @SAM ya @Azeem tag ho tabhi act kare, random messages ignore
