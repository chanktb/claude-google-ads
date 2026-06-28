#!/usr/bin/env python
"""
money_leak_report.py — turn a raw Google-Ads pull bundle into ONE comprehensive, PER-CAMPAIGN audit.

Architecture (see references/per-campaign-report-template.md):
  AUDIT.html = Account panel (every account-level setting LISTED + rated good/bad)
             + one VISUAL-EXPLAINER block per active campaign: each quantitative metric is a CHART
               (ROAS semicircle gauge, budget ring, channel donut, device/geo bars, hourly heatmap),
               every setting follows DATA -> VERDICT (GOOD/WATCH/FIX/VERIFY) -> ACTION, with a scorecard.
             + Action Plan.
Every leak is localized to its campaign; only account-wide items sit in the account panel.

PIPELINE (model-tier dispatch):
  1. Routine sub-agent runs the PULL MANIFEST -> writes bundle.json (extended schema below)
  2. Judge writes audit-result.json (the score) next to it
  3. Scout runs:  python money_leak_report.py bundle.json --out-dir .
  4. Judge adds verify-in-UI verdicts.

BUNDLE SCHEMA (bundle.json) — every section optional; report degrades gracefully:
{
  "meta": {"account_name","customer_id","window_start","window_end"},
  "active_campaigns": [{"id","name","channel_type","budget_micros","target_roas","bidding_strategy_type",
      "system_status","primary_status","brand_guidelines_enabled","geo_target_type",  # 7=PRESENCE_OR_INTEREST,5=PRESENCE
      "cost_micros","conversions","conversions_value","impressions","clicks"}],
  "enhanced_conversions": true,   # customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled (bool)
  "channel":   [{"campaign_id","ad_network_type","cost_micros","conversions","conversions_value","clicks"}],
  "device":    [{"campaign_id","device","cost_micros","conversions","conversions_value","clicks"}],
  "geo":       [{"campaign_id","geo_region_id","location_type","cost_micros","conversions","conversions_value","clicks"}],
  "geo_names": {"<id>":"<name>"},
  "dayparting":[{"campaign_id","hour","day_of_week","cost_micros","conversions","conversions_value"}],
  "schedule":  [{"campaign_id","day_of_week","start_hour","end_hour","bid_modifier"}],
  "assets":    [{"campaign_id","field_type","text","cost_micros","conversions","conversions_value","clicks"}],  # headlines (ft2)
  "descriptions":[{"campaign_id","text","cost_micros","conversions","clicks"}],
  "extensions":[{"campaign_id","field_type"}],                              # counts
  "ext_text":  [{"campaign_id","field_type","text"}],                       # sitelink/callout/snippet TEXT
  "negatives": [{"campaign_id","source","text","match_type"}],             # campaign + shared-list + brand-list
  "final_urls":[{"campaign_id","url"}],
  "signals":   [{"campaign_id","asset_group_id","search_theme","audience"}],
  "conversion_lag":[{"campaign_id"?,"conversion_lag_bucket","conversions","conversions_value"}],
  "change_events": [{"change_date_time","change_resource_type","user_email","campaign_name"}],
  "products":  [{"campaign_id","product_item_id","product_title","cost_micros","conversions","conversions_value","clicks"}],
  "merchant":  {"merchant_id","active","disapproved","expiring","real_issues":{},"burner_status":[{"title","status","action"}]}
}
"""
import json, sys, argparse, os, math
from collections import defaultdict
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8")

def _pdate(s):
    try: return datetime.strptime((s or "")[:10],"%Y-%m-%d")
    except Exception: return datetime.min

NET = {2:"Search",3:"Search Partners",4:"Display",7:"Mixed",8:"YouTube",9:"Google TV",10:"Google-owned",11:"Gmail",12:"Discover",13:"Maps"}
DEV = {1:"Unknown",2:"Mobile",3:"Tablet",4:"Desktop",5:"Connected TV",6:"Other"}
# AssetFieldType — real Google Ads API enum (verified live): SITELINK=13, CALLOUT=11, CALL=16,
# LONG_HEADLINE=18, LOGO=21, PORTRAIT_IMAGE=24, PRICE=26, STRUCTURED_SNIPPET=27.
FT  = {2:"Headline",3:"Description",4:"Mandatory text",5:"Image",6:"Media bundle",7:"YouTube video",10:"Promotion",
       11:"Callout",13:"Sitelink",16:"Call",18:"Long headline/Biz name",19:"Business name",21:"Logo",
       24:"Portrait image",26:"Price",27:"Structured snippet"}
SNIPPET_FT, PRICE_FT = 27, 26
SYS = {2:"ENABLED",3:"LEARNING_NEW",9:"LIMITED_BY_CPC_CEILING",11:"LIMITED_BY_DATA",12:"LIMITED_BY_BUDGET",
       15:"LIMITED_BY_INVENTORY",17:"MISCONFIGURED_CONV_TYPES",18:"MISCONFIGURED_CONV_SETTINGS"}
PRI = {2:"ELIGIBLE",3:"PAUSED",4:"REMOVED",5:"ENDED",6:"PENDING",7:"MISCONFIGURED",8:"LIMITED",9:"LEARNING",10:"NOT_ELIGIBLE"}
CT  = {2:"SEARCH",3:"DISPLAY",4:"SHOPPING",6:"VIDEO",7:"MULTI_CHANNEL",8:"LOCAL",9:"SMART",10:"PERFORMANCE_MAX",11:"LOCAL_SERVICES",13:"DEMAND_GEN"}
CLAG= {2:"<1d",3:"1-2d",4:"2-3d",5:"3-4d",6:"4-5d",7:"5-6d",8:"6-7d",9:"7-8d",10:"8-9d",11:"9-10d",16:"14-21d",17:"21-30d"}
CER = {2:"Ad",3:"AdGroup",4:"AdGroupCriterion",5:"Campaign",6:"CampaignBudget",7:"AdGroupBidModifier",8:"CampaignCriterion",13:"AdGroupAd",16:"CampaignAsset",21:"AssetGroup",22:"AssetGroupAsset",23:"ListingGroupFilter",24:"AssetGroupSignal"}
DOW = {2:"Mon",3:"Tue",4:"Wed",5:"Thu",6:"Fri",7:"Sat",8:"Sun"}
GRADE_C={"A":"#1e8e5a","B":"#2563eb","C":"#c8860a","D":"#d9622b","F":"#c0392b"}
SEVC={"Critical":"#b91c1c","High":"#dc2626","Medium":"#d97706","Investigate":"#d97706","Low":"#16a34a","Opportunity":"#2563eb","PASS":"#16a34a","WARNING":"#d97706","FAIL":"#dc2626"}
COOLDOWN_DAYS=14
GEO_MIN, HOUR_MIN, DEV_MIN, ASSET_MIN, PROD_MIN = 50.0, 80.0, 50.0, 30.0, 30.0
WEAK=0.5; MARGINAL=0.7

def ctname(v): return CT.get(v, v if isinstance(v,str) else str(v))
def is_pmax(c): return c.get("channel_type") in (10,"10","PERFORMANCE_MAX")
def d(x): return (x or 0)/1e6
def roas(v,c): return (v/c) if c else 0.0
def sysname(v): return SYS.get(v, v if isinstance(v,str) else str(v))
def devname(v): return DEV.get(v, v if isinstance(v,str) else str(v))
def netname(v): return NET.get(v, v if isinstance(v,str) else str(v))
def _clean(s):
    if not s: return s
    for a,bb in (("â€”","—"),("â€“","–"),("â€™","'"),("â€œ",'"'),("â€\x9d",'"'),("â€¦","…"),("Â "," "),("Â","")):
        s=s.replace(a,bb)
    return s
def esc(s): return str(s if s is not None else "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def score_color(v):
    return ("#1e8e5a" if v>=90 else "#2563eb" if v>=75 else "#c8860a" if v>=60 else "#d9622b" if v>=40 else "#c0392b")
def donut_svg(score):
    r,cx=54,68; circ=2*math.pi*r; dash=circ*max(0,min(100,score))/100; col=score_color(score)
    return (f'<svg width="120" height="120" viewBox="0 0 136 136" role="img" aria-label="Health score {score}">'
            f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="#eef2f7" stroke-width="12"/>'
            f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="{col}" stroke-width="12" stroke-linecap="round" '
            f'stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cx})"/>'
            f'<text x="{cx}" y="{cx-1}" text-anchor="middle" font-size="34" font-weight="800" fill="#0f172a">{score}</text>'
            f'<text x="{cx}" y="{cx+20}" text-anchor="middle" font-size="12" fill="#64748b">/ 100</text></svg>')

# ---------- chart builders (visual explainer) ----------
def gauge_svg(rv,tg):
    sc=max(rv,tg,0.1)*1.55
    def pt(fr):
        ang=math.radians(180-180*min(1.0,fr/sc)); return 95+72*math.cos(ang),95-72*math.sin(ang)
    ex,ey=pt(rv); col="#10b981" if (not tg or rv>=tg) else ("#f59e0b" if rv>=0.8*tg else "#ef4444")
    tick=""
    if tg:
        ox,oy=pt(tg); a2=math.radians(180-180*min(1.0,tg/sc)); ix,iy=95+58*math.cos(a2),95-58*math.sin(a2)
        tick=f'<line x1="{ox:.1f}" y1="{oy:.1f}" x2="{ix:.1f}" y2="{iy:.1f}" stroke="#0f172a" stroke-width="2.5"/>'
    sub=f"&#9650; target {tg:g}x &middot; {rv/tg*100:.0f}%" if tg else "brand &middot; no tROAS"
    return (f'<svg viewBox="0 0 190 112" width="168"><path d="M23 95 A72 72 0 0 1 167 95" fill="none" stroke="#eef2f7" stroke-width="13" stroke-linecap="round"/>'
            f'<path d="M23 95 A72 72 0 0 1 {ex:.1f} {ey:.1f}" fill="none" stroke="{col}" stroke-width="13" stroke-linecap="round"/>{tick}'
            f'<text x="95" y="84" text-anchor="middle" font-size="28" font-weight="800" fill="#0f172a">{rv:.2f}x</text>'
            f'<text x="95" y="103" text-anchor="middle" font-size="10.5" fill="#64748b">{sub}</text></svg>')
def ring_svg(util):
    circ=2*math.pi*34; pct=min(1.0,util); col="#10b981" if 0.3<=util<0.9 else ("#f59e0b" if util>=0.9 else "#94a3b8"); dash=circ*pct
    return (f'<svg viewBox="0 0 90 90" width="84"><circle cx="45" cy="45" r="34" fill="none" stroke="#eef2f7" stroke-width="11"/>'
            f'<circle cx="45" cy="45" r="34" fill="none" stroke="{col}" stroke-width="11" stroke-linecap="round" stroke-dasharray="{dash:.1f} {circ-dash:.1f}" transform="rotate(-90 45 45)"/>'
            f'<text x="45" y="42" text-anchor="middle" font-size="17" font-weight="800" fill="#0f172a">{util*100:.0f}%</text>'
            f'<text x="45" y="58" text-anchor="middle" font-size="7.5" fill="#64748b">of budget/day</text></svg>')
def donut2(frac,label,sub):
    circ=2*math.pi*34; aa=circ*max(0.0,min(1.0,frac))
    return (f'<svg viewBox="0 0 90 90" width="84"><circle cx="45" cy="45" r="34" fill="none" stroke="#eef2f7" stroke-width="11"/>'
            f'<circle cx="45" cy="45" r="34" fill="none" stroke="#2563eb" stroke-width="11" stroke-dasharray="{aa:.1f} {circ-aa:.1f}" transform="rotate(-90 45 45)"/>'
            f'<circle cx="45" cy="45" r="34" fill="none" stroke="#f59e0b" stroke-width="11" stroke-dasharray="{circ-aa:.1f} {aa:.1f}" stroke-dashoffset="{-aa:.1f}" transform="rotate(-90 45 45)"/>'
            f'<text x="45" y="42" text-anchor="middle" font-size="15" font-weight="800" fill="#0f172a">{label}</text>'
            f'<text x="45" y="57" text-anchor="middle" font-size="8" fill="#64748b">{sub}</text></svg>')
def hbars(rows,maxv,w=560,bx=120):
    h=len(rows)*23+6; out=[f'<svg viewBox="0 0 {w} {h}" width="100%"><g font-size="12" fill="#475569">']
    for i,(lab,val,col,vt) in enumerate(rows):
        y=i*23+16; bw=max(5,val/maxv*(w-bx-150)) if maxv else 5
        out.append(f'<text x="0" y="{y}">{esc(lab)}</text><rect x="{bx}" y="{y-11}" width="{bw:.0f}" height="14" rx="3" fill="{col}"/><text x="{bx+bw+6:.0f}" y="{y}" fill="#0f172a">{esc(vt)}</text>')
    out.append('</g></svg>'); return "".join(out)
def heat(hc):
    out=['<svg viewBox="0 0 296 56" width="100%"><g>']
    for hh in range(24):
        x=4+hh*11.5; out.append(f'<rect x="{x:.1f}" y="10" width="10" height="24" rx="2" fill="{hc.get(hh,"#e2e8f0")}"/>')
    out.append('<g font-size="9" fill="#94a3b8"><text x="4" y="48">0h</text><text x="73" y="48">6h</text><text x="142" y="48">12h</text><text x="211" y="48">18h</text><text x="266" y="48">23h</text></g></g></svg>')
    return "".join(out)
def meter_html(frac,col): return f'<span class="meter"><i style="width:{max(3,min(100,frac*100)):.0f}%;background:{col}"></i></span>'
VC={"GOOD":"v-good","WATCH":"v-watch","FIX":"v-fix","VERIFY":"v-ui"}
VD={"GOOD":"d-good","WATCH":"d-watch","FIX":"d-fix","VERIFY":"d-ui"}
def vchip(v): return f'<span class="verdict {VC.get(v,"v-nt")}">{v}</span>'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("--out-dir",default=".")
    ap.add_argument("--audit-result",default=None)
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
    b=json.load(open(a.bundle,encoding="utf-8-sig"))
    ar=None; arp=a.audit_result
    if not arp:
        cand=os.path.join(os.path.dirname(os.path.abspath(a.bundle)),"audit-result.json")
        if os.path.exists(cand): arp=cand
    if arp and os.path.exists(arp):
        try: ar=json.load(open(arp,encoding="utf-8-sig"))
        except Exception: ar=None

    meta=b.get("meta",{}); camps=b.get("active_campaigns",[])
    name={c["id"]:c.get("name",str(c["id"])) for c in camps}
    tot_cost=sum(d(c.get("cost_micros")) for c in camps)
    tot_val=sum(float(c.get("conversions_value",0) or 0) for c in camps)
    blended=roas(tot_val,tot_cost)
    maxroas=max([roas(float(c.get("conversions_value",0) or 0),d(c.get("cost_micros"))) for c in camps]+[0.01])

    def bycamp(key):
        o=defaultdict(list)
        for r in b.get(key,[]) or []: o[r.get("campaign_id")].append(r)
        return o
    chan_c=bycamp("channel"); dev_c=bycamp("device"); geo_c=bycamp("geo"); dp_c=bycamp("dayparting")
    asset_c=bycamp("assets"); desc_c=bycamp("descriptions"); ext_c=bycamp("extensions"); exttx_c=bycamp("ext_text")
    neg_c=bycamp("negatives"); furl_c=bycamp("final_urls"); sig_c=bycamp("signals"); prod_c=bycamp("products")
    sch_c=bycamp("schedule")
    geo_names=b.get("geo_names",{})
    merch=b.get("merchant") or {}
    # `pulled` manifest: the bundle declares which dimensions were FULLY pulled (all campaigns). A dimension
    # not listed = NOT pulled → render VERIFY, never a confident finding. This stops a truncated/partial pull
    # (e.g. signals fetched for only 3 of 7 PMax) from producing FALSE "0 signal" findings. If the bundle
    # omits `pulled` entirely, fall back to key-presence (back-compat).
    _pulled_decl = b.get("pulled")
    def was_pulled(dim):
        return (dim in _pulled_decl) if _pulled_decl is not None else (b.get(dim) not in (None, []))
    # Account-wide signal presence: if SOME PMax carries signals, a lone campaign at 0 is more likely an
    # incomplete per-campaign pull than a true gap → soften that finding instead of a confident "No signal".
    _any_pmax_sig = any((r.get("audience") or "").strip() for r in (b.get("signals") or []))
    def merch_status(title):
        t=(title or "").lower()
        for x in merch.get("burner_status",[]) or []:
            key=(x.get("title","") or "").lower().split(" $")[0]
            toks=[w for w in key.replace("/"," ").split() if len(w)>3][:3]
            if toks and all(w in t for w in toks): return x
        return None

    findings=[]
    def add(cid,sev,usd,dim,title,body,kind="hard"): findings.append({"cid":cid,"sev":sev,"usd":usd,"dim":dim,"title":title,"body":body,"kind":kind})

    # ---------- per-campaign diagnostics ----------
    for c in camps:
        cid=c["id"]; cost=d(c.get("cost_micros")); val=float(c.get("conversions_value",0) or 0)
        conv=float(c.get("conversions",0) or 0); r=roas(val,cost); tgt=float(c.get("target_roas") or 0)
        sysn=sysname(c.get("system_status"))
        if sysn=="LIMITED_BY_BUDGET" and (not tgt or r>=tgt):
            add(cid,"Opportunity",0,"bid/target","Budget-limited & on-target — scale headroom",
                f"system_status=LIMITED_BY_BUDGET with ROAS {r:.2f}x{(' >= target '+format(tgt,'g')+'x') if tgt else ''}. Scale +10-15% (Mondays, after cooldown); do NOT raise tROAS.","free")
        elif sysn=="LIMITED_BY_INVENTORY":
            add(cid,"Medium",0,"bid/target","tROAS too high — starving on inventory",
                "system_status=LIMITED_BY_INVENTORY: target so high the system can't find enough auctions. Lower tROAS -10-15%.","free")
        elif sysn in ("MISCONFIGURED_CONV_TYPES","MISCONFIGURED_CONV_SETTINGS"):
            add(cid,"High",0,"bid/target","Conversion misconfiguration on this campaign",
                f"system_status={sysn} — fix conversion goals/settings before any scale.","free")
        ch=defaultdict(lambda:[0.0,0.0])
        for r2 in chan_c.get(cid,[]):
            n=r2.get("ad_network_type"); ch[n][0]+=d(r2.get("cost_micros")); ch[n][1]+=float(r2.get("conversions",0) or 0)
        # Only flag non-search burn when per-network CONVERSIONS were actually pulled. If channel rows carry
        # cost but no conversions (a cost-only pull), every campaign would look like "0 conv burn" — false.
        ch_has_conv = sum(v[1] for v in ch.values()) > 0
        burn=[(netname(n),v) for n,v in ch.items() if n not in (2,3) and v[0]>=10 and v[1]==0] if ch_has_conv else []
        if burn:
            tt=sum(v[0] for _,v in burn); worst=", ".join(f"{nm} ${v[0]:.0f}" for nm,v in sorted(burn,key=lambda x:-x[1][0])[:3])
            add(cid,"Investigate" if tt<60 else "Medium",tt,"channel",f"Non-Search burn ${tt:.0f}/mo, 0 conv",
                f"WHERE: {worst} (named surfaces, not 'Display'). PMax levers limited — account placement exclusions / Content Suitability [UI]. If <$50/mo, monitor.")
        dvv=defaultdict(lambda:[0.0,0.0,0.0])
        for r2 in dev_c.get(cid,[]):
            k=r2.get("device"); dvv[k][0]+=d(r2.get("cost_micros")); dvv[k][1]+=float(r2.get("conversions",0) or 0); dvv[k][2]+=float(r2.get("conversions_value",0) or 0)
        for k,(co,cv,vl) in dvv.items():
            if co<DEV_MIN: continue
            if cv==0: add(cid,"Medium",co,"device",f"Device waste — {devname(k)} ${co:,.0f}, 0 conv",
                f"WHERE: {devname(k)}. Exclude where supported (e.g. Connected TV).")
            elif roas(vl,co)<WEAK*blended and blended:
                add(cid,"Investigate",co*(1-roas(vl,co)/blended),"device",f"Weak device — {devname(k)} ROAS {roas(vl,co):.2f}x",
                    f"WHERE: {devname(k)}. Device bid -% (Search) / note (PMax control limited).","directional")
        greg=defaultdict(lambda:[0.0,0.0,0.0,0]); i_cost=i_val=g_cost=0.0
        for r2 in geo_c.get(cid,[]):
            rid=r2.get("geo_region_id"); co=d(r2.get("cost_micros")); g_cost+=co
            greg[rid][0]+=co; greg[rid][1]+=float(r2.get("conversions",0) or 0); greg[rid][2]+=float(r2.get("conversions_value",0) or 0); greg[rid][3]+=int(r2.get("clicks",0) or 0)
            if r2.get("location_type")==2: i_cost+=co; i_val+=float(r2.get("conversions_value",0) or 0)
        if i_cost>=GEO_MIN and g_cost and i_cost/g_cost>=0.05:
            ir=roas(i_val,i_cost); short=i_cost*(1-ir/blended) if blended and ir<blended else 0
            add(cid,"Investigate",short,"geo",f"Presence-or-Interest leak ${i_cost:,.0f}/mo (ROAS {ir:.2f}x)",
                f"{i_cost/g_cost*100:.0f}% of geo spend serves AREA-OF-INTEREST. Switch to PRESENCE [UI: geo_target_type_setting].","directional")
        weakg=[]
        for rid,(co,cv,vl,ck) in sorted(greg.items(),key=lambda x:-x[1][0]):
            if co<GEO_MIN: continue
            nm=geo_names.get(str(rid),geo_names.get(rid,str(rid)))
            rr=roas(vl,co)
            if cv==0: weakg.append((nm,co,0.0,co,True))
            elif rr<WEAK*blended and blended: weakg.append((nm,co,rr,co*(1-rr/blended),False))
        if weakg:
            tot_short=sum(w[3] for w in weakg); tot_spend=sum(w[1] for w in weakg)
            top=sorted(weakg,key=lambda x:-x[3])[:6]; more=len(weakg)-len(top)
            lst="; ".join(f"{nm} ${co:,.0f}@{'0conv' if z else f'{rr:.2f}x'}" for nm,co,rr,sh,z in top)
            add(cid,"Investigate" if tot_short<200 else "Medium",tot_short,"geo",
                f"Geo waste — {len(weakg)} weak/0-conv regions, ${tot_short:,.0f}/mo shortfall",
                f"WHERE: {lst}"+(f" (+{more} more)" if more>0 else "")+f". ${tot_spend:,.0f} spend sub-{WEAK*blended:.1f}x ROAS. Exclude or apply a location bid adjustment (supported on PMax too — not exclusion-only).","directional")
        if dp_c.get(cid):
            hh=defaultdict(lambda:[0.0,0.0,0.0])
            for r2 in dp_c[cid]:
                k=r2.get("hour"); hh[k][0]+=d(r2.get("cost_micros")); hh[k][1]+=float(r2.get("conversions",0) or 0); hh[k][2]+=float(r2.get("conversions_value",0) or 0)
            weakh=[]
            for hr,(co,cv,vl) in sorted(hh.items()):
                if co<HOUR_MIN: continue
                rr=roas(vl,co)
                if (cv==0 or rr<WEAK*blended) and blended: weakh.append((hr,co,rr,co*(1-rr/blended) if rr<blended else co))
            if weakh:
                ts=sum(w[3] for w in weakh); top=sorted(weakh,key=lambda x:-x[3])[:6]
                lst=", ".join(f"{hr:02d}:00 ${co:,.0f}@{rr:.1f}x" for hr,co,rr,sh in top)
                add(cid,"Investigate",ts,"daypart",f"Weak hours — {len(weakh)} hours, ${ts:,.0f}/mo shortfall",
                    f"WHERE: {lst}{' (+'+str(len(weakh)-len(top))+' more)' if len(weakh)>len(top) else ''}. Apply an ad-schedule bid adjustment (supported on PMax too) or tighten the schedule window.","directional")
        ecnt=defaultdict(int)
        src=exttx_c.get(cid) or ext_c.get(cid) or []
        for r2 in src: ecnt[r2.get("field_type")]+=1
        miss=[]
        if ecnt.get(13,0)<4: miss.append(f"sitelinks {ecnt.get(13,0)}")
        if ecnt.get(11,0)<4: miss.append(f"callouts {ecnt.get(11,0)}")
        if ecnt.get(SNIPPET_FT,0)<1: miss.append("snippets 0")
        if miss:
            add(cid,"High" if ecnt.get(13,0)==0 else "Low",0,"extensions",f"Thin extensions — {', '.join(miss)}",
                "Add 6+ sitelinks, 8-10 callouts, a snippet set. Free SERP real estate / CTR lift.","free")
        heads=[r2 for r2 in asset_c.get(cid,[]) if r2.get("field_type")==2]
        hburn=[r2 for r2 in heads if d(r2.get("cost_micros"))>=ASSET_MIN and float(r2.get("conversions",0) or 0)==0]
        if hburn:
            lst="; ".join(f'"{_clean(r2.get("text",""))}" ${d(r2.get("cost_micros")):.0f}' for r2 in sorted(hburn,key=lambda x:-d(x.get("cost_micros")))[:5])
            add(cid,"Low",0,"adcopy",f"Ad-copy review — {len(hburn)} headlines spend, 0 conv",
                f"{lst}. Read the PATTERN; validate with Asset Experiments, don't pause singles.","free")
        if is_pmax(c) and was_pulled("signals"):
            rows=sig_c.get(cid,[]); aud=sum(1 for r2 in rows if (r2.get("audience") or "").strip()); thm=sum(1 for r2 in rows if (r2.get("search_theme") or "").strip())
            if aud==0 and _any_pmax_sig:
                add(cid,"Investigate",0,"signals","0 audience signals — confirm","Other PMax campaigns in this account DO carry signals, so a 0 here may be an incomplete per-campaign pull. Confirm in the UI; if truly none, add >=1 (customer-match / site visitors).","directional")
            elif aud==0:
                add(cid,"High",0,"signals","No audience signal","No PMax campaign has a signal seed — Smart Bidding has nothing to learn from. Add >=1: customer-match → website-visitors → custom segment.","free")
            elif thm<5: add(cid,"Low",0,"signals",f"Thin search themes ({thm})","Add specific intent-led search themes (up to 50/AG).","free")
        pa=defaultdict(lambda:[0.0,0.0,0,""])
        for r2 in prod_c.get(cid,[]):
            k=r2.get("product_item_id"); pa[k][0]+=d(r2.get("cost_micros")); pa[k][1]+=float(r2.get("conversions",0) or 0); pa[k][2]+=int(r2.get("clicks",0) or 0); pa[k][3]=_clean(r2.get("product_title","")) or pa[k][3]
        pburn=sorted([(t,co,ck) for k,(co,cv,ck,t) in pa.items() if co>=PROD_MIN and cv==0 and ck>=10],key=lambda x:-x[1])
        if pburn:
            tt=sum(co for _,co,_ in pburn); tops=[]
            for t,co,ck in pburn[:6]:
                ms=merch_status(t); tag=f" [{ms['status']}]" if ms else ""
                tops.append(f'"{t[:40]}" ${co:.0f}/{ck}clk{tag}')
            add(cid,"High",tt,"products",f"Product waste — {len(pburn)} products ${tt:,.0f}/mo, 0 conv",
                f"WHERE: {'; '.join(tops)}. Check Merchant FIRST — OOS → restock/exclude; in-stock → price/intent.")

    timeline=[]; per=defaultdict(list)
    if b.get("change_events"):
        for e in b["change_events"]:
            cn=e.get("campaign_name","?"); dt=(e.get("change_date_time") or "")[:19]
            rt=CER.get(e.get("change_resource_type"),e.get("change_resource_type"))
            per[cn].append((dt,rt,e.get("user_email",""))); timeline.append((dt,cn,rt,e.get("user_email","")))
        timeline.sort(reverse=True)
        try: ref=datetime.strptime((meta.get("window_end") or "")[:10],"%Y-%m-%d")
        except Exception: ref=None
        nm2id={v:k for k,v in name.items()}
        if ref:
            cutoff=ref-timedelta(days=COOLDOWN_DAYS)
            for cn,evs in per.items():
                if cn in nm2id and any(x[0] and _pdate(x[0])>=cutoff for x in evs):
                    add(nm2id[cn],"High",0,"change","Cooldown active — don't scale yet",
                        f"Changed within {COOLDOWN_DAYS}d. Hold budget/target moves until Smart Bidding stabilizes.","free")
                bud=[x for x in evs if x[1] in ("CampaignBudget","Campaign")]
                if cn in nm2id and len(bud)>=3:
                    add(nm2id[cn],"Medium",0,"change",f"Whipsawing — {len(bud)} budget/campaign changes/30d",
                        "Over-tinkering resets learning. Hold to one change per cooldown.","free")

    pm=[c for c in camps if is_pmax(c)]
    for c in pm:
        c["_roas"]=roas(float(c.get("conversions_value",0) or 0),d(c.get("cost_micros")))
        c["_util"]=(d(c.get("cost_micros"))/30)/d(c.get("budget_micros")) if c.get("budget_micros") else 0
    if len(pm)>=2:
        lo=min(pm,key=lambda x:x["_roas"]); hi=max(pm,key=lambda x:x["_roas"])
        if lo["id"]!=hi["id"] and hi["_roas"]-lo["_roas"]>0.3 and lo["_util"]>=0.85 and hi["_util"]<0.92:
            headroom=max(0.0,d(hi["budget_micros"])*30.4-d(hi["cost_micros"]))
            move=min(0.15*d(lo["cost_micros"]),headroom) if headroom>0 else 0.15*d(lo["cost_micros"])
            gain=move*(hi["_roas"]-lo["_roas"])*MARGINAL
            add(None,"High",gain,"alloc",f"Budget misallocation across PMax — {name[lo['id']]} → {name[hi['id']]}",
                f"Shift ~${move:,.0f}/mo from {name[lo['id']]} (ROAS {lo['_roas']:.2f}x, ~{lo['_util']*100:.0f}% budget) to {name[hi['id']]} (ROAS {hi['_roas']:.2f}x, headroom). Est +${gain:,.0f}/mo. +10-15% steps, Mondays, after cooldown.")
    lag_line=""
    if b.get("conversion_lag"):
        lt=sum(float(r.get("conversions",0) or 0) for r in b["conversion_lag"]) or 1
        w7=sum(float(r.get("conversions",0) or 0) for r in b["conversion_lag"] if r.get("conversion_lag_bucket") in (2,3,4,5,6,7,8))
        same=sum(float(r.get("conversions",0) or 0) for r in b["conversion_lag"] if r.get("conversion_lag_bucket")==2)
        beyond=1-w7/lt
        trust="short-window ROAS is TRUSTWORTHY" if beyond<0.15 else "short-window ROAS UNDERSTATES — judge on 30-day"
        lag_line=f"Conversion lag: {same/lt*100:.0f}% same-day, {w7/lt*100:.0f}% within 7d → {trust}."
        if beyond>=0.15:
            add(None,"Medium",0,"lag","Conversion-lag gate — recent-window ROAS understated",
                f"{beyond*100:.0f}% of conversions land >7 days after click. Judge new/post-change on a 30-day window.","free")

    findings.sort(key=lambda x:-x["usd"])
    quant=sum(f["usd"] for f in findings if f["kind"]=="hard")
    directional=sum(f["usd"] for f in findings if f["kind"]=="directional")
    change_line=f"{len(b['change_events'])} changes in 30d across {len(per)} campaigns." if b.get("change_events") else ""
    acct_find=[f for f in findings if f["cid"] is None]
    cfind=defaultdict(list)
    for f in findings:
        if f["cid"] is not None: cfind[f["cid"]].append(f)

    # ============================ HTML (per-campaign visual explainer) ============================
    score=ar.get("health_score") if ar else None; grade=ar.get("grade","") if ar else ""
    gcol=GRADE_C.get(grade,"#2563eb"); headline=ar.get("headline") if ar else ""
    def ccard(title,verdict,svg,cnt,cap="",action="",wide=False):
        cnt[verdict]=cnt.get(verdict,0)+1
        foot=(f'<div class="cap">{cap}</div>' if cap else '')+(f'<div class="act">&rarr; {action}</div>' if action else '')
        return f'<div class="cc{" wide" if wide else ""}"><div class="ct">{title} {vchip(verdict)}</div><div class="svgc">{svg}</div>{foot}</div>'
    def vrow(verdict,label,data,cnt,action="",mtr=""):
        cnt[verdict]=cnt.get(verdict,0)+1
        act=f'<div class="raction">&rarr; {action}</div>' if action else ''
        return f'<div class="row"><span class="dot {VD.get(verdict,"d-nt")}"></span><div class="rmain"><div class="rlabel">{label} {mtr}<span class="rdata">{data}</span></div>{act}</div>{vchip(verdict)}</div>'
    def sc_html(cnt):
        out=[]
        for v,cls in (("GOOD","s-good"),("WATCH","s-watch"),("FIX","s-fix"),("VERIFY","s-ui")):
            if cnt.get(v): out.append(f'<span class="pill {cls}">{cnt[v]} {v.lower()}</span>')
        return "".join(out)

    H=[f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(meta.get('account_name','Account'))} — Google Ads Audit</title><style>
*{{box-sizing:border-box}}body{{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Arial;color:#0f172a;background:#f6f8fb}}
.wrap{{max-width:960px;margin:0 auto;padding:20px 16px 60px}}
.hero{{background:#fff;border:1px solid #eef1f5;border-radius:18px;padding:18px 22px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;box-shadow:0 1px 3px rgba(15,23,42,.05)}}
.hero h1{{margin:0;font-size:21px;font-weight:800;letter-spacing:-.01em}}.hero .sub{{font-size:12.5px;color:#64748b;margin-top:3px}}
.grade{{display:inline-block;font-size:16px;font-weight:800;color:#fff;background:{gcol};border-radius:8px;padding:1px 10px;margin-left:8px;vertical-align:middle}}
.kpis{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}}.kpi{{background:#f8fafc;border:1px solid #eef1f5;border-radius:10px;padding:7px 12px}}
.kpi .v{{font-weight:800;font-size:16px}}.kpi .l{{font-size:10.5px;color:#64748b}}
.note{{font-size:12.5px;border-radius:10px;padding:9px 13px;margin:12px 0;background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af}}
.legend{{font-size:11px;color:#64748b;padding:6px 2px;display:flex;gap:14px;flex-wrap:wrap}}.legend span{{display:inline-flex;align-items:center;gap:5px}}.lg{{width:8px;height:8px;border-radius:99px}}
h2.t{{font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;color:#64748b;margin:22px 2px 2px;font-weight:700}}
.card{{background:#fff;border:1px solid #eef1f5;border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.05);margin:14px 0;overflow:hidden}}
.chead{{padding:15px 20px;display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;border-bottom:1px solid #eef1f5}}
.chead h3{{margin:0;font-size:16px;font-weight:700;letter-spacing:-.01em}}.chead .sub{{font-size:12px;color:#64748b;margin-top:3px}}
.pill{{font-size:11px;font-weight:700;border-radius:999px;padding:3px 10px;display:inline-block}}.tier{{background:#0f172a;color:#fff}}.score{{display:flex;gap:6px;flex-wrap:wrap}}
.s-good{{background:#ecfdf5;color:#059669}}.s-watch{{background:#fffbeb;color:#b45309}}.s-fix{{background:#fef2f2;color:#b91c1c}}.s-ui{{background:#eff6ff;color:#1d4ed8}}
.gtitle{{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;padding:14px 16px 4px;display:flex;align-items:center;gap:7px}}.gtitle .sq{{width:9px;height:9px;border-radius:3px}}
.charts{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:8px 14px 4px}}@media(max-width:640px){{.charts{{grid-template-columns:repeat(2,1fr)}}}}
.cc{{border:1px solid #eef1f5;border-radius:14px;padding:10px 12px}}.cc.wide{{grid-column:span 3}}@media(max-width:640px){{.cc.wide{{grid-column:span 2}}}}
.cc .ct{{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.03em;display:flex;justify-content:space-between;align-items:center;gap:6px}}
.svgc{{display:flex;justify-content:center;padding:4px 0}}.cc .cap{{font-size:11.5px;color:#64748b;margin-top:4px}}.cc .act{{font-size:11.5px;color:#4338ca;margin-top:3px}}
.verdict{{font-size:10px;font-weight:800;border-radius:6px;padding:2px 6px;letter-spacing:.02em}}
.v-good{{background:#ecfdf5;color:#059669}}.v-watch{{background:#fffbeb;color:#b45309}}.v-fix{{background:#fef2f2;color:#dc2626}}.v-ui{{background:#eff6ff;color:#2563eb}}.v-nt{{background:#f1f5f9;color:#64748b}}
.row{{display:flex;gap:11px;padding:9px 16px;align-items:flex-start}}.row+.row{{border-top:1px solid #f5f7fa}}
.dot{{width:9px;height:9px;border-radius:99px;margin-top:5px;flex:none}}.d-good{{background:#10b981}}.d-watch{{background:#f59e0b}}.d-fix{{background:#ef4444}}.d-ui{{background:#3b82f6}}.d-nt{{background:#94a3b8}}
.rmain{{flex:1;min-width:0}}.rlabel{{font-weight:600;font-size:13.5px}}.rdata{{font-weight:400;color:#64748b;font-size:12.5px}}
.raction{{font-size:12.5px;color:#4338ca;margin-top:3px}}.raction b{{color:#3730a3}}
.meter{{display:inline-block;width:54px;height:7px;border-radius:99px;background:#eef2f7;vertical-align:middle;margin:0 6px;position:relative;overflow:hidden}}.meter i{{position:absolute;left:0;top:0;height:100%;border-radius:99px}}
.ap h4{{margin:12px 16px 4px;font-size:13px}}.ap ul{{margin:0;padding:0 16px 8px 32px}}.ap li{{font-size:13px;margin:5px 0}}
.muted{{color:#64748b;font-size:12px}}.foot{{text-align:center;color:#94a3b8;font-size:12px;margin-top:30px}}
</style></head><body><div class="wrap">
<h2 class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden">Per-campaign visual Google Ads audit for {esc(meta.get('account_name','Account'))}.</h2>
<div class="hero">
{('<div>'+donut_svg(score)+'</div>') if score is not None else ''}
<div style="flex:1;min-width:240px">
<h1>{esc(meta.get('account_name','Account'))} — Google Ads Audit{('<span class="grade">'+esc(grade)+'</span>') if grade else ''}</h1>
<div class="sub">Customer {esc(meta.get('customer_id',''))} · {esc(meta.get('window_start',''))} → {esc(meta.get('window_end',''))} · per-campaign visual explainer</div>
<div class="kpis">
<div class="kpi"><div class="v">${tot_cost:,.0f}</div><div class="l">Spend (30d)</div></div>
<div class="kpi"><div class="v">{blended:.2f}x</div><div class="l">Blended ROAS</div></div>
<div class="kpi"><div class="v">${quant:,.0f}</div><div class="l">Recoverable / mo</div></div>
<div class="kpi"><div class="v">{len(camps)}</div><div class="l">Active campaigns</div></div>
</div></div></div>
<div class="legend"><span><span class="lg" style="background:#10b981"></span>GOOD</span><span><span class="lg" style="background:#f59e0b"></span>WATCH</span><span><span class="lg" style="background:#ef4444"></span>FIX</span><span><span class="lg" style="background:#3b82f6"></span>VERIFY (UI)</span></div>"""]
    if headline: H.append(f'<div class="note" style="background:#eef4fb;border-color:#bfdbfe;color:#1e3a5f">{esc(headline)}</div>')
    if directional>0:
        ndir=len([f for f in findings if f["kind"]=="directional"])
        H.append(f'<div class="note">📊 <b>${quant:,.0f}/mo</b> concrete recoverable (cuts + reallocation, non-overlapping). Plus {ndir} <b>directional</b> geo/daypart opportunities flagged per campaign — single-dimension estimates that overlap, so NOT summed.</div>')
    if lag_line: H.append(f'<div class="note" style="background:#ecfdf5;border-color:#a7f3d0;color:#065f46">⏱ {esc(lag_line)}</div>')

    # ---------- ACCOUNT PANEL — every account-level setting listed + rated ----------
    acnt={}; arows=[]
    if ar:
        for cat in ar.get("categories",[]):
            for f in (cat.get("fixable") or []):
                st=f.get("status"); v="GOOD" if st=="PASS" else ("FIX" if st=="FAIL" else "WATCH")
                arows.append(vrow(v,esc(f.get("title","")),f'[{esc(cat.get("name",""))}] {esc(f.get("id",""))}',acnt,action=esc(f.get("fix","")) if v!="GOOD" else ""))
            for u in (cat.get("unverified") or []):
                arows.append(vrow("VERIFY",esc(u.get("title","")),esc((u.get("note","") or "")[:160]),acnt,action="Confirm in UI."))
    if lag_line:
        arows.append(vrow("GOOD" if "TRUSTWORTHY" in lag_line else "WATCH","Conversion lag",esc(lag_line),acnt))
    allsrc=defaultdict(int)
    for r2 in b.get("negatives",[]) or []: allsrc[r2.get("source","?")]+=1
    acct_lists=[s for s in allsrc if "account" in s.lower() or "brand" in s.lower()]
    if acct_lists:
        arows.append(vrow("GOOD","Account negative &amp; brand-exclusion lists",esc(" · ".join(acct_lists[:8]))+" <span style=\"color:#94a3b8\">(applied across PMax)</span>",acnt,action=""))
    for f in acct_find:
        v="FIX" if f["sev"] in ("High","Critical") else "WATCH"
        arows.append(vrow(v,esc(f["title"]),esc(f["body"][:150]),acnt,action="See campaigns affected."))
    H.append('<h2 class="t">Account-level settings — listed & rated</h2>')
    H.append(f'<div class="card"><div class="chead"><div><h3>{esc(meta.get("account_name","Account"))} — account</h3><div class="sub">{len(camps)} active · ${tot_cost:,.0f}/30d · {blended:.2f}x blended</div></div><div class="score">{sc_html(acnt)}</div></div><div>')
    H.append("".join(arows) or '<div class="row"><span class="muted">No account-level items.</span></div>')
    H.append('</div></div>')

    # ---------- PER-CAMPAIGN visual blocks ----------
    H.append('<h2 class="t">Per-campaign deep-dives</h2>')
    for c in sorted(camps,key=lambda x:-d(x.get("cost_micros"))):
        cid=c["id"]; cost=d(c.get("cost_micros")); val=float(c.get("conversions_value",0) or 0); conv=float(c.get("conversions",0) or 0)
        r=roas(val,cost); tgt=float(c.get("target_roas") or 0); sysn=sysname(c.get("system_status"))
        rref=r if r>0 else blended
        dimset=[f["dim"] for f in cfind.get(cid,[])]
        cnt={}
        # --- charts ---
        charts=[]
        roas_v="GOOD" if (not tgt or r>=tgt) else ("WATCH" if r>=0.8*tgt else "FIX")
        charts.append(ccard("ROAS vs target",roas_v,gauge_svg(r,tgt),cnt,cap=("Beating target." if roas_v=="GOOD" else "Below target — review.")))
        util=(cost/30)/d(c.get("budget_micros")) if c.get("budget_micros") else 0
        budget_v="GOOD" if 0.3<=util<0.9 else "WATCH"
        bud_act="Budget-capped &amp; on-target → scale +10-15% after cooldown." if (util>=0.9 and roas_v=="GOOD") else ("Underpacing — check delivery/bids." if util<0.3 else "")
        charts.append(ccard("Budget pacing",budget_v,ring_svg(util),cnt,action=bud_act))
        chs=defaultdict(float)
        for r2 in chan_c.get(cid,[]): chs[r2.get("ad_network_type")]+=d(r2.get("cost_micros"))
        if not chs:
            # No channel rows: NOT pulled. segments.ad_network_type IS available (incl. PMax) — this is a
            # pull gap to fix, NOT a UI-only field. Never render a fabricated "0% / GOOD" donut.
            charts.append(ccard("Channel mix","VERIFY",donut2(0,"—","n/a"),cnt,cap="channel not pulled — re-run (segments.ad_network_type works, incl. PMax)"))
        else:
            cs=sum(v for n,v in chs.items() if n in (2,3)); ot=sum(v for n,v in chs.items() if n not in (2,3)); ctot=cs+ot or 1
            channel_v="WATCH" if "channel" in dimset else "GOOD"
            oth=" · ".join(f"{netname(n)} ${v:.0f}" for n,v in sorted(chs.items(),key=lambda x:-x[1]) if n not in (2,3))[:90]
            charts.append(ccard("Channel mix",channel_v,donut2(cs/ctot,f"{cs/ctot*100:.0f}%","Search"),cnt,cap=("other "+f"{ot/ctot*100:.1f}% — "+esc(oth)) if ot>0 else "all on Search/Shopping"))
        dvv=defaultdict(lambda:[0.0,0.0])
        for r2 in dev_c.get(cid,[]):
            k=r2.get("device"); dvv[k][0]+=d(r2.get("cost_micros")); dvv[k][1]+=float(r2.get("conversions_value",0) or 0)
        devrows=[]
        for k,(co,vl) in sorted(dvv.items(),key=lambda x:-x[1][0]):
            if co<1: continue
            rr=roas(vl,co); col="#10b981" if rr>=0.85*rref else ("#f59e0b" if rr>=0.5*rref else "#ef4444")
            devrows.append((devname(k),co,col,f"${co:,.0f} · {rr:.2f}x"))
        devf=[f for f in cfind.get(cid,[]) if f["dim"]=="device"]
        device_v="FIX" if any("waste" in f["title"] for f in devf) else ("WATCH" if devf else "GOOD")
        if devrows:
            charts.append(ccard("Device — spend &amp; ROAS",device_v,hbars(devrows,max(x[1] for x in devrows),w=560,bx=78),cnt,action=(devf[0]["body"] if devf else ""),wide=True))
        greg=defaultdict(lambda:[0.0,0.0,0.0])
        for r2 in geo_c.get(cid,[]):
            rid=r2.get("geo_region_id"); greg[rid][0]+=d(r2.get("cost_micros")); greg[rid][1]+=float(r2.get("conversions",0) or 0); greg[rid][2]+=float(r2.get("conversions_value",0) or 0)
        def _gname(rid): return (geo_names.get(str(rid),geo_names.get(rid,str(rid))) or "").split(",")[0]
        # Two ACTIONABLE lists, not a flat "top spend": WINNERS to keep/scale, DRAINS to exclude/bid-down.
        winners=[]; drains=[]
        for rid,(co,cv,vl) in greg.items():
            rr=roas(vl,co)
            if co>=GEO_MIN and vl>0 and rr>=0.85*rref:        # high value + ROAS at/above the campaign's bar
                winners.append((_gname(rid),vl,"#10b981",f"${vl:,.0f} val · {rr:.1f}x"))
            elif (vl<=0 and co>=20) or (co>=GEO_MIN and rr<WEAK*rref):
                # TWO kinds of drain: (a) spend with ZERO conversion value = 100% waste (low $ floor so we
                # don't hide them); (b) meaningful spend at ROAS well below the bar. Rank by $ WASTED.
                wasted = co if vl<=0 else co*(1-rr/rref)
                drains.append((_gname(rid),co,"#ef4444",f"${co:,.0f} cost · {'0 value (100% waste)' if vl<=0 else f'{rr:.1f}x'}",wasted))
        winners=sorted(winners,key=lambda x:-x[1])[:6]
        drains=[t[:4] for t in sorted(drains,key=lambda x:-x[4])[:8]]
        if winners:
            charts.append(ccard("Geo — winners (keep / scale): high value &amp; ROAS","GOOD",
                hbars(winners,max(x[1] for x in winners),w=560,bx=120),cnt,
                action="These states convert efficiently — protect budget / geo bid-up (Search & PMax both support location bid adjustments).",wide=True))
        if drains:
            dtot=sum(x[1] for x in drains); nz=sum(1 for t in drains if "0 value" in t[3])
            charts.append(ccard("Geo — drains (exclude / bid-down): zero-value + low-ROAS spend","FIX" if dtot>=200 else "WATCH",
                hbars(drains,max(x[1] for x in drains),w=560,bx=120),cnt,
                action=f"${dtot:,.0f}/mo in drains"+(f" ({nz} states at 0 conversion value = pure waste)" if nz else "")+" — exclude or apply a location bid adjustment (supported on PMax too, not exclusion-only).",wide=True))
        if not winners and not drains and greg:
            charts.append(ccard("Geo","GOOD",hbars([( _gname(r),v[0],"#10b981",f"${v[0]:,.0f} · {roas(v[2],v[0]):.1f}x") for r,v in sorted(greg.items(),key=lambda x:-x[1][0])[:5]],max(v[0] for v in greg.values()),w=560,bx=120),cnt,action="All meaningful regions near target.",wide=True))
        hc={}
        if dp_c.get(cid):
            hh=defaultdict(lambda:[0.0,0.0])
            for r2 in dp_c[cid]:
                k=r2.get("hour"); hh[k][0]+=d(r2.get("cost_micros")); hh[k][1]+=float(r2.get("conversions_value",0) or 0)
            for k,(co,vl) in hh.items():
                if not isinstance(k,int):
                    try: k=int(k)
                    except Exception: continue
                if co<15: hc[k]="#e2e8f0"
                else:
                    rr=roas(vl,co); hc[k]="#10b981" if rr>=0.85*rref else ("#f59e0b" if rr>=0.5*rref else "#ef4444")
        sched_v="WATCH" if "daypart" in dimset else "GOOD"
        if hc:
            sf=[f for f in cfind.get(cid,[]) if f["dim"]=="daypart"]
            charts.append(ccard("Schedule — ROAS by hour",sched_v,heat(hc),cnt,action=(sf[0]["body"] if sf else "Gray = off / low spend."),wide=True))
        # --- rows: creative & AG, settings, negatives/products, stability ---
        groups=[]
        # creative
        crows=[]
        ec=defaultdict(int); etx=defaultdict(list)
        src=exttx_c.get(cid) or ext_c.get(cid) or []
        for r2 in src: ec[r2.get("field_type")]+=1
        for r2 in (exttx_c.get(cid) or []): etx[r2.get("field_type")].append(_clean(r2.get("text","")))
        sl=ec.get(13,0); cou=ec.get(11,0); sn=ec.get(SNIPPET_FT,0)
        sl_v="GOOD" if sl>=4 else ("WATCH" if sl>=1 else "FIX")
        crows.append(vrow(sl_v,"Sitelinks",esc(", ".join(t for t in etx.get(13,[]) if t)[:90]) or f"{sl} links",cnt,
            action=("Add sitelinks (6+ with descriptions)." if sl_v!="GOOD" else ""),mtr=meter_html(min(1,sl/6),"#10b981" if sl_v=="GOOD" else ("#f59e0b" if sl_v=="WATCH" else "#ef4444"))))
        cou_v="GOOD" if cou>=8 else ("WATCH" if cou>=1 else "FIX")
        crows.append(vrow(cou_v,"Callouts",esc(", ".join(t for t in etx.get(11,[]) if t)[:80]) or f"{cou}",cnt,
            action=("Add to 8-10 callouts." if cou_v!="GOOD" else ""),mtr=meter_html(min(1,cou/8),"#10b981" if cou_v=="GOOD" else ("#f59e0b" if cou_v=="WATCH" else "#ef4444"))))
        sn_v="GOOD" if sn>=1 else "FIX"
        crows.append(vrow(sn_v,"Structured snippets",(esc(", ".join(t for t in etx.get(SNIPPET_FT,[]) if t)[:70]) if sn else "0 sets"),cnt,
            action=("Add a snippet set (e.g. Brands: …)." if sn_v!="GOOD" else ""),mtr=meter_html(0.04 if sn==0 else 1,"#ef4444" if sn==0 else "#10b981")))
        if is_pmax(c) and not was_pulled("signals"):
            crows.append(vrow("VERIFY","Audience signals","not pulled — re-run asset_group_signal for EVERY PMax (don't stop early)",cnt,action="Loop all PMax campaigns; partial pull = false '0 signal' findings."))
        elif is_pmax(c):
            srows=sig_c.get(cid,[]); aud=len({(x.get("audience") or "").strip() for x in srows if (x.get("audience") or "").strip()}); thm=len({(x.get("search_theme") or "").strip() for x in srows if (x.get("search_theme") or "").strip()})
            # GOOD if seeded; if 0 here but OTHER PMax have signals, it's likely an incomplete pull → VERIFY,
            # not a confident FIX. Only a true account-wide absence is a FIX.
            sig_v="GOOD" if aud>=1 else ("VERIFY" if _any_pmax_sig else "FIX")
            sig_txt=(f"{aud} attached — seeded" if aud else ("0 here — confirm (other PMax have signals; pull may be partial)" if _any_pmax_sig else "0 attached — none in the account"))
            crows.append(vrow(sig_v,"Audience signals",sig_txt,cnt,action=("" if aud else ("Confirm in UI, then add if truly missing." if _any_pmax_sig else "Add >=1 signal (customer-match / site visitors).")),mtr=meter_html(min(1,aud/3),"#10b981" if aud else "#ef4444")))
            thm_v="GOOD" if thm>=5 else "WATCH"
            thms=sorted({(x.get("search_theme") or "").strip() for x in srows if (x.get("search_theme") or "").strip()})
            crows.append(vrow(thm_v,"Search themes",f"{thm} — "+esc(", ".join(thms[:6])),cnt,action=("Add intent-led themes." if thm<5 else "")))
        heads=sorted([x for x in asset_c.get(cid,[]) if x.get("field_type")==2],key=lambda x:-d(x.get("cost_micros")))
        hburn=[x for x in heads if d(x.get("cost_micros"))>=ASSET_MIN and float(x.get("conversions",0) or 0)==0]
        if not heads and "assets" not in b:
            # not pulled — segments/asset_group_asset ARE available; this is a pull gap, not UI-only
            crows.append(vrow("VERIFY","Headlines","not pulled — re-run (asset_group_asset)",cnt,action="Pull asset_group_asset / ad_group_ad assets to assess."))
        else:
            txts=[t for t in (f'"{esc(_clean(x.get("text","")))}" ${d(x.get("cost_micros")):.0f}' if x.get("text") else "" for x in heads[:4]) if t]
            hl_v="WATCH" if hburn else ("GOOD" if heads else "WATCH")
            # heads present but text empty = a counts-only pull (text IS pullable via asset_group_asset +
            # asset.text_asset.text — re-pull WITH text + metrics). Don't blame the MCP.
            hl_txt="; ".join(txts) or (f"{len(heads)} headlines — text not in bundle (re-pull asset_group_asset WITH asset.text_asset.text + metrics)" if heads else "none pulled")
            crows.append(vrow(hl_v,"Headlines",hl_txt,cnt,action=(f"{len(hburn)} headlines spent at 0 conv — read pattern, test via Asset Experiments." if hburn else "")))
        descs=desc_c.get(cid,[])
        if descs or "descriptions" in b:
            crows.append(vrow("GOOD" if descs else "WATCH","Descriptions",(esc("; ".join('"'+_clean(x.get("text",""))+'"' for x in descs[:2]))[:140] if descs else "none pulled"),cnt))
        groups.append(("#8b5cf6","Creative &amp; assets (asset-group level)",crows))
        # negatives / products
        nprows=[]
        ng=neg_c.get(cid,[]); bysrc=defaultdict(int)
        for r2 in ng: bysrc[r2.get("source","?")]+=1
        if "negatives" in b:
            nprows.append(vrow("GOOD" if bysrc else "WATCH","Negatives &amp; brand blocks",(esc(" · ".join(f"{s} ({n})" for s,n in list(bysrc.items())[:6])) if bysrc else "none for this campaign"),cnt,action=("" if bysrc else "Attach negative + brand-exclusion lists.")))
        else:
            # GUARD-2: never claim "no negatives" without having pulled campaign_criterion + shared_set + brand-list.
            nprows.append(vrow("VERIFY","Negatives &amp; brand blocks","not pulled — verify shared lists + brand exclusions",cnt,action="Pull campaign_shared_set → shared_criterion AND brand_list exclusions before judging coverage."))
        prf=[f for f in cfind.get(cid,[]) if f["dim"]=="products"]
        if prf:
            nprows.append(vrow("WATCH","0-conv product burners",esc(prf[0]["title"]),cnt,action="Check Merchant: OOS → restock/exclude; in-stock → price/intent."))
        if nprows: groups.append(("#10b981","Negatives &amp; products",nprows))
        # settings verify-in-UI
        srows2=[]
        # Location targeting type READS via campaign.geo_target_type_setting — show it, don't punt to UI.
        gt=c.get("geo_target_type") or (c.get("geo_target_type_setting") or {}).get("positive_geo_target_type")
        if gt in (7,"7","PRESENCE_OR_INTEREST"):
            srows2.append(vrow("FIX","Location targeting","Presence-OR-Interest — serves users merely interested in the geo",cnt,action="Switch to Presence-only (People in your targeted locations) to cut interest-based waste."))
        elif gt in (5,"5","PRESENCE"):
            srows2.append(vrow("GOOD","Location targeting","Presence-only (people physically in the geo)",cnt))
        # Enhanced Conversions READS at customer level (set once on the bundle meta).
        ec=(b.get("measurement") or {}).get("enhanced_conversions") if isinstance(b.get("measurement"),dict) else b.get("enhanced_conversions")
        if ec is True: srows2.append(vrow("GOOD","Enhanced Conversions","enabled (customer.conversion_tracking_setting)",cnt))
        elif ec is False: srows2.append(vrow("FIX","Enhanced Conversions","NOT enabled — turn on for signal recovery",cnt,action="Enable Enhanced Conversions in the conversion settings."))
        # Only the genuinely-unreadable settings remain verify-in-UI (confirmed 2026-06-28).
        srows2.append(vrow("VERIFY","FUE · asset automation · content suitability","not in the Ads API on this version",cnt,action="Verify in UI: Final URL Expansion + URL exclusions, auto-created assets/text customization, content-suitability/placement exclusions."))
        srows2.append(vrow("VERIFY","Consent Mode v2 · server-side/CAPI","tag-side config — not an Ads entity",cnt,action="Verify in GTM / Google Tag Diagnostics (not a pull failure)."))
        chf=[f for f in cfind.get(cid,[]) if f["dim"]=="change"]
        if chf:
            srows2.append(vrow("WATCH","Stability / cooldown",esc(chf[0]["title"]),cnt,action="Hold budget/target moves until Smart Bidding restabilizes."))
        groups.append(("#3b82f6","Settings &amp; stability",srows2))

        syscol="#10b981" if sysn=="ENABLED" else ("#f59e0b" if ("LIMITED" in sysn or "LEARNING" in sysn) else "#ef4444" if "MISCONF" in sysn else "#94a3b8")
        # assemble camp card (scorecard uses cnt now filled)
        H.append(f'<div class="card"><div class="chead"><div><h3>{esc(c.get("name"))} <span class="pill tier">{esc(ctname(c.get("channel_type")))}</span></h3>'
                 f'<div class="sub">${cost:,.0f} → ${val:,.0f} value · {conv:.0f} conv · <span style="color:{syscol};font-weight:700">{esc(sysn)}</span> · budget ${d(c.get("budget_micros")):,.0f}/day</div>'
                 f'<div class="score" style="margin-top:8px">{sc_html(cnt)}</div></div></div>')
        H.append('<div class="gtitle"><span class="sq" style="background:#6366f1"></span>Performance &amp; delivery — every metric as a chart</div>')
        H.append('<div class="charts">'+"".join(charts)+'</div>')
        for col,title,rws in groups:
            if not rws: continue
            H.append(f'<div class="gtitle"><span class="sq" style="background:{col}"></span>{title}</div><div>'+"".join(rws)+'</div>')
        H.append('</div>')

    # ---------- Merchant + action plan ----------
    if merch:
        m_active = merch.get("active") or 0      # null-safe: a connected GMC with feed health NOT pulled has active=None
        m_disap  = merch.get("disapproved") or 0
        m_exp    = merch.get("expiring") or 0
        H.append('<h2 class="t">Account product feed (Merchant Center)</h2>')
        if merch.get("active") is None and not merch.get("real_issues"):
            H.append(f'<div class="card"><div style="padding:13px 18px;font-size:13px">GMC {esc(merch.get("merchant_id",""))} connected — <b>feed health not pulled this pass</b>. Verify OOS / disapprovals / GTIN in Merchant Center (highest-$ ecom lever).</div></div>')
        else:
            H.append(f'<div class="card"><div style="padding:13px 18px;font-size:13px">GMC {esc(merch.get("merchant_id",""))} · <b>{m_active:,} active</b> · {m_disap} disapproved ({m_disap/max(m_active,1)*100:.2f}%) · {m_exp} expiring.'
                     + (f' Real disapprovals: <b>{esc(", ".join(f"{k} {v}" for k,v in merch.get("real_issues",{}).items()))}</b>' if merch.get("real_issues") else '') + '</div></div>')
    H.append('<h2 class="t">Action plan</h2><div class="card ap">')
    today=[f for f in findings if f["sev"] in ("Critical","High") and f["dim"] in ("signals","products","bid/target","change","extensions")]
    week=[f for f in findings if f["dim"] in ("geo","daypart","channel","device","alloc") and f["usd"]>0]
    qwins=(ar.get("quick_wins") if ar else []) or []
    H.append('<h4>Today (verify-wins + cooldown-safe)</h4><ul>')
    for q in qwins[:4]: H.append(f'<li><b>{esc(q.get("title"))}</b> <span class="muted">({esc(q.get("minutes"))} min — {esc(q.get("impact"))})</span></li>')
    for f in today[:5]: H.append(f'<li><b>{esc(name.get(f["cid"],"account"))}:</b> {esc(f["title"])}</li>')
    H.append('</ul><h4>This week (localized, by $)</h4><ul>')
    for f in week[:8]: H.append(f'<li><b>{esc(name.get(f["cid"],"account"))}:</b> {esc(f["title"])}'+(f' — ~${f["usd"]:,.0f}/mo' if f["usd"] else '')+'</li>')
    H.append('</ul></div>')
    H.append('<div class="foot">Generated by claude-google-ads · per-campaign visual explainer · each item: data → verdict → action · [VERIFY]=API can\'t see it, check UI · $ over a 30-day window.</div></div></body></html>')
    out_html=os.path.join(a.out_dir,"AUDIT.html"); open(out_html,"w",encoding="utf-8").write("\n".join(H))

    # ===== compact MD companions =====
    L=[f"# {meta.get('account_name','Account')} — Money-Leak Report (per-campaign)",
       f"Spend ${tot_cost:,.0f} · {blended:.2f}x blended · ~${quant:,.0f}/mo recoverable · {len(camps)} active.",""]
    if acct_find:
        L.append("## Account-level")
        for f in acct_find: L.append(f"- [{f['sev']}] {f['title']}"+(f" — ~${f['usd']:,.0f}/mo" if f['usd'] else ""))
    for c in sorted(camps,key=lambda x:-d(x.get("cost_micros"))):
        cid=c["id"]; mine=cfind.get(cid,[])
        L.append(f"\n## {c.get('name')} — ROAS {roas(float(c.get('conversions_value',0) or 0),d(c.get('cost_micros'))):.2f}x")
        if mine:
            for f in sorted(mine,key=lambda x:-x['usd']): L.append(f"- [{f['sev']}] {f['title']}"+(f" — ~${f['usd']:,.0f}/mo" if f['usd'] else "")+f"\n  {f['body']}")
        else: L.append("- (clean)")
    open(os.path.join(a.out_dir,"MONEY-LEAK-REPORT.md"),"w",encoding="utf-8").write("\n".join(L))
    open(os.path.join(a.out_dir,"DETAILED-ACCOUNT-REPORT.md"),"w",encoding="utf-8").write("\n".join(L))

    print(f"Wrote AUDIT.html (per-campaign visual) + MD to {a.out_dir}")
    print(f"  {len(findings)} findings ({len(acct_find)} account, {len(findings)-len(acct_find)} per-camp) · ${quant:,.0f}/mo concrete + ${directional:,.0f}/mo directional · blended {blended:.2f}x"
          + (f" · score {ar.get('health_score')}/{ar.get('grade')}" if ar else ""))

if __name__=="__main__":
    main()
