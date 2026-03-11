#!/usr/bin/env python3
"""Regenerates index.html from results.json — supports CBC, Blumenau and BBC."""
import json

BASE = '/Users/hboavent/Projects/personal/concursos-resultados/'

with open(BASE + 'results.json', 'r', encoding='utf-8') as f:
    DATA = json.load(f)

# ---------- Build brewery structures per year ----------

def sort_entries(entries):
    order = {'Ouro': 0, 'Prata': 1, 'Bronze': 2}
    return sorted(entries, key=lambda e: (e['style'].lower(), order.get(e['medal'], 9)))

def build_brewery_data(year):
    """Collect brewery entries from all three contests, then split into multi/only buckets."""
    contests = {}
    for contest in ('cbc', 'blumenau', 'bbc'):
        breweries = {}
        for style, cd in DATA['data'].items():
            for e in cd.get(contest, {}).get(year, []):
                bl = e['brewery'].lower()
                if bl not in breweries:
                    breweries[bl] = {'display': e['brewery'], 'entries': []}
                breweries[bl]['entries'].append({
                    'style': style, 'medal': e['medal'],
                    'beer': e['beer'], 'state': e.get('state', '')
                })
        contests[contest] = breweries

    cbc, blu, bbc = contests['cbc'], contests['blumenau'], contests['bbc']
    all_keys = set(cbc) | set(blu) | set(bbc)

    # Only contests that actually have data this year
    active = [c for c in ('cbc', 'blumenau', 'bbc') if contests[c]]

    multi, only_cbc, only_blu, only_bbc = [], [], [], []

    for k in all_keys:
        in_cbc = k in cbc
        in_blu = k in blu
        in_bbc = k in bbc
        display = (cbc.get(k) or blu.get(k) or bbc.get(k))['display']

        # "múltiplos" = present in every active contest this year
        if all(k in contests[c] for c in active):
            multi.append({
                'name':     display,
                'cbc':      sort_entries(cbc[k]['entries']) if in_cbc else [],
                'blumenau': sort_entries(blu[k]['entries']) if in_blu else [],
                'bbc':      sort_entries(bbc[k]['entries']) if in_bbc else [],
            })
        elif in_cbc and not in_blu and not in_bbc:
            only_cbc.append({'name': display, 'entries': sort_entries(cbc[k]['entries'])})
        elif in_blu and not in_cbc and not in_bbc:
            only_blu.append({'name': display, 'entries': sort_entries(blu[k]['entries'])})
        elif in_bbc and not in_cbc and not in_blu:
            only_bbc.append({'name': display, 'entries': sort_entries(bbc[k]['entries'])})

    key_fn = lambda x: x['name'].lower()
    return {
        'multi':   sorted(multi,    key=key_fn),
        'onlyCbc': sorted(only_cbc, key=key_fn),
        'onlyBlu': sorted(only_blu, key=key_fn),
        'onlyBbc': sorted(only_bbc, key=key_fn),
    }

# Pre-compute brewery data, stats, and active-contest list per year
BREWERY_DATA_BY_YEAR = {}
STATS_BY_YEAR = {}
CONTESTS_BY_YEAR = {}

for year in DATA['years']:
    bd = build_brewery_data(year)
    BREWERY_DATA_BY_YEAR[year] = bd
    STATS_BY_YEAR[year] = {
        'stylesCbc': sum(1 for s in DATA['styles'] if DATA['data'][s].get('cbc', {}).get(year)),
        'stylesBlu': sum(1 for s in DATA['styles'] if DATA['data'][s].get('blumenau', {}).get(year)),
        'stylesBbc': sum(1 for s in DATA['styles'] if DATA['data'][s].get('bbc', {}).get(year)),
        'multi':     len(bd['multi']),
    }
    CONTESTS_BY_YEAR[year] = [
        c for c in ('cbc', 'blumenau', 'bbc')
        if any(DATA['data'][s].get(c, {}).get(year) for s in DATA['styles'])
    ]

RJ  = json.dumps(DATA,                 ensure_ascii=False, separators=(',', ':'))
BDJ = json.dumps(BREWERY_DATA_BY_YEAR, ensure_ascii=False, separators=(',', ':'))
STJ = json.dumps(STATS_BY_YEAR,        ensure_ascii=False, separators=(',', ':'))
CBJ = json.dumps(CONTESTS_BY_YEAR,     ensure_ascii=False, separators=(',', ':'))

HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pint.Network — Análise de Concursos Comerciais</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg:         #0d0d0d;
  --surface:    #141414;
  --card:       #1c1c1c;
  --card-hover: #232323;
  --border:     #2d2d2d;
  --amber:      #f5c230;
  --amber-dim:  #c49a20;
  --cream:      #f0f0f0;
  --muted:      #787878;
  --faint:      #2a2a2a;
  --gold:       #ffd700;
  --gold2:      #c9960c;
  --silver:     #c8c8c8;
  --silver2:    #8a8a8a;
  --bronze:     #cd7f32;
  --bronze2:    #8b5010;
  --match:      #3d6b2a;
  --match-text: #7ec850;
  --blue:       #5ba3d0;
  --green:      #4caf78;
  --green-dim:  #2e7a50;
  --sidebar-w:  320px;
  --header-h:   60px;
  --base-fs:    15px;
}

html,body{
  height:100%;
  background:var(--bg);
  color:var(--cream);
  font-family:'DM Sans',sans-serif;
  font-size:var(--base-fs);
  overflow:hidden;
}

/* ─── HEADER ─────────────────────────────────────────────── */
header{
  position:fixed;top:0;left:0;right:0;
  height:var(--header-h);
  background:var(--surface);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;
  padding:0 18px;gap:14px;
  z-index:200;
}
.header-brand{
  display:flex;align-items:center;gap:12px;
  flex-shrink:0;
}
.header-logo-img{
  height:30px;
  width:auto;
  display:block;
}
.header-divider{
  width:1px;height:20px;
  background:var(--border);
  flex-shrink:0;
}
.header-subtitle{
  font-family:'DM Sans',sans-serif;
  font-size:12px;
  color:var(--muted);
  white-space:nowrap;
}
.header-nav{
  display:flex;gap:2px;margin-left:4px;
}
.nav-link{
  font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;
  padding:3px 11px;border-radius:12px;
  border:1px solid var(--border);color:var(--muted);
  text-decoration:none;cursor:pointer;transition:all .15s;letter-spacing:.03em;
}
.nav-link:hover{border-color:var(--amber-dim);color:var(--amber)}
.nav-link.active{background:var(--amber);color:var(--bg);border-color:var(--amber)}
.year-filter{
  display:flex;gap:4px;
  margin-left:4px;
}
.year-btn{
  font-family:'IBM Plex Mono',monospace;
  font-size:11px;font-weight:500;
  padding:3px 9px;
  border-radius:12px;
  border:1px solid var(--border);
  background:transparent;
  color:var(--muted);
  cursor:pointer;
  transition:all .15s;
  letter-spacing:.03em;
}
.year-btn.active{
  background:var(--amber);
  color:var(--bg);
  border-color:var(--amber);
}
.header-stats{
  display:flex;gap:10px;margin-left:auto;
}
.stat-pill{
  font-family:'IBM Plex Mono',monospace;
  font-size:11px;
  padding:4px 11px;
  border-radius:20px;
  border:1px solid var(--border);
  color:var(--muted);
  white-space:nowrap;
  cursor:default;
  transition:all .15s;
}
.stat-pill b{color:var(--amber);font-weight:500}
.stat-pill.match{
  border-color:rgba(126,200,80,.35);
  color:var(--match-text);
  cursor:pointer;
}
.stat-pill.match:hover{
  background:rgba(61,107,42,.2);
  border-color:var(--match-text);
}
.stat-pill.cbc-a b{color:var(--amber)}
.stat-pill.cbc-b b{color:var(--blue)}
.stat-pill.cbc-c b{color:var(--green)}

/* ─── LAYOUT ─────────────────────────────────────────────── */
.app{
  display:flex;
  height:100vh;
  padding-top:var(--header-h);
}

/* ─── SIDEBAR ─────────────────────────────────────────────── */
.sidebar{
  width:var(--sidebar-w);
  flex-shrink:0;
  display:flex;
  flex-direction:column;
  border-right:1px solid var(--border);
  background:var(--surface);
  overflow:hidden;
}
.search-wrap{
  padding:12px 12px 8px;
  border-bottom:1px solid var(--border);
}
.search-input{
  width:100%;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:6px;
  padding:9px 12px 9px 34px;
  color:var(--cream);
  font-family:'DM Sans',sans-serif;
  font-size:14px;
  outline:none;
  transition:border-color .2s;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%237a6540' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E");
  background-repeat:no-repeat;
  background-position:11px 50%;
}
.search-input:focus{border-color:var(--amber-dim)}
.search-input::placeholder{color:var(--muted)}

.filter-bar{
  display:flex;gap:5px;padding:8px 12px;
  border-bottom:1px solid var(--border);
  flex-wrap:wrap;
}
.filter-btn{
  font-size:11px;font-family:'IBM Plex Mono',monospace;
  padding:4px 9px;border-radius:4px;
  border:1px solid var(--border);
  background:transparent;
  color:var(--muted);
  cursor:pointer;
  transition:all .15s;
  white-space:nowrap;
}
.filter-btn:hover{border-color:var(--amber-dim);color:var(--amber)}
.filter-btn.active{background:var(--amber);color:var(--bg);border-color:var(--amber)}

.style-count{
  padding:5px 12px;
  font-size:11px;
  font-family:'IBM Plex Mono',monospace;
  color:var(--muted);
  border-bottom:1px solid var(--border);
}

.style-list{
  overflow-y:auto;
  flex:1;
}
.style-list::-webkit-scrollbar{width:4px}
.style-list::-webkit-scrollbar-track{background:transparent}
.style-list::-webkit-scrollbar-thumb{background:var(--faint);border-radius:2px}
.style-list::-webkit-scrollbar-thumb:hover{background:var(--amber-dim)}

.style-item{
  display:flex;align-items:center;
  padding:10px 12px;
  cursor:pointer;
  border-left:3px solid transparent;
  transition:all .15s;
  gap:8px;
}
.style-item:hover{background:var(--card-hover);border-left-color:var(--amber-dim)}
.style-item.active{
  background:var(--card);
  border-left-color:var(--amber);
}
.style-item.match-style .style-name::after{
  content:'◆';
  font-size:7px;
  color:var(--match-text);
  margin-left:5px;
  vertical-align:middle;
}
.style-name{
  font-size:13.5px;
  color:var(--cream);
  flex:1;
  line-height:1.35;
}
.style-item.active .style-name{color:var(--amber)}
.style-dots{
  display:flex;gap:3px;flex-shrink:0;
}
.dot{width:6px;height:6px;border-radius:50%;background:var(--faint)}
.dot.a{background:var(--amber-dim)}
.dot.b{background:#4a7fa0}
.dot.c{background:var(--green-dim)}

/* ─── MAIN ─────────────────────────────────────────────── */
.main{
  flex:1;
  overflow-y:auto;
  display:flex;
  flex-direction:column;
}
.main::-webkit-scrollbar{width:6px}
.main::-webkit-scrollbar-track{background:transparent}
.main::-webkit-scrollbar-thumb{background:var(--faint);border-radius:3px}
.main::-webkit-scrollbar-thumb:hover{background:var(--amber-dim)}

/* ─── MAIN STYLE ACCORDION ─────────────────────────────── */
#main-style-list{
  padding:0;
}

.ms-item{
  border-bottom:1px solid var(--border);
  transition:background .15s;
}
.ms-header{
  display:flex;align-items:center;
  padding:14px 20px;
  cursor:pointer;
  gap:10px;
  transition:background .15s;
}
.ms-header:hover{background:var(--card-hover)}
.ms-item.active>.ms-header{
  background:var(--card);
}
.ms-item.selected>.ms-header{
  border-left:3px solid var(--amber);
  padding-left:17px;
  background:var(--card);
}
.ms-name{
  font-size:18px;
  color:var(--cream);
  flex:1;
  line-height:1.35;
  font-weight:600;
}
.ms-item.selected>.ms-header .ms-name{color:var(--amber)}
.ms-dots{display:flex;gap:3px;flex-shrink:0}
.ms-match-tag{
  font-size:9px;
  font-family:'IBM Plex Mono',monospace;
  color:var(--match-text);
  background:rgba(61,107,42,.2);
  border:1px solid rgba(126,200,80,.25);
  border-radius:3px;
  padding:1px 5px;
  flex-shrink:0;
}
.ms-chevron{
  color:var(--muted);
  font-size:11px;
  flex-shrink:0;
  transition:transform .2s;
  font-family:'IBM Plex Mono',monospace;
}
.ms-item.selected>.ms-header .ms-chevron{
  color:var(--amber);
}

.ms-detail{
  padding:16px 20px 20px;
  background:var(--card);
  border-top:1px solid var(--border);
  animation:slideDown .25s cubic-bezier(.2,.8,.3,1);
}
@keyframes slideDown{
  from{opacity:0;transform:translateY(-6px)}
  to{opacity:1;transform:translateY(0)}
}

/* ─── MATCH BADGE ─────────────────────────────────────── */
.match-badge{
  display:none;align-items:center;gap:6px;
  font-family:'IBM Plex Mono',monospace;
  font-size:10px;
  color:var(--match-text);
  background:rgba(61,107,42,.15);
  border:1px solid rgba(126,200,80,.2);
  border-radius:4px;
  padding:4px 10px;
  margin-bottom:14px;
}
.match-badge.visible{display:flex}

/* ─── COMPARISON GRID ─────────────────────────────────── */
.comp-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:14px;
}

/* ─── COMPETITION CARD ─────────────────────────────────── */
.comp-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:10px;
  overflow:hidden;
}
.comp-header{
  padding:11px 15px 9px;
  border-bottom:1px solid var(--border);
}
.comp-name{
  font-family:'IBM Plex Mono',monospace;
  font-size:10px;
  font-weight:500;
  letter-spacing:.08em;
  text-transform:uppercase;
  line-height:1.4;
}
.comp-a .comp-name{color:var(--amber)}
.comp-b .comp-name{color:var(--blue)}
.comp-c .comp-name{color:var(--green)}
.comp-no-data{
  padding:24px 15px;
  text-align:center;
  color:var(--muted);
  font-size:12px;
  font-style:italic;
}

/* ─── MEDAL ENTRY ─────────────────────────────────────── */
.medal-entry{
  display:flex;align-items:flex-start;
  padding:11px 15px;
  gap:11px;
  border-bottom:1px solid var(--border);
  transition:background .15s;
}
.medal-entry:last-child{border-bottom:none}
.medal-entry:hover{background:var(--card-hover)}
.medal-entry.is-match{background:rgba(61,107,42,.08)}
.medal-entry.is-match:hover{background:rgba(61,107,42,.14)}

.medal-badge{
  flex-shrink:0;
  width:42px;height:42px;
  border-radius:50%;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-family:'IBM Plex Mono',monospace;
  font-size:8px;
  font-weight:500;
  letter-spacing:.04em;
  line-height:1.2;
  text-align:center;
}
.medal-badge.ouro{
  background:radial-gradient(circle at 35% 35%, #ffe55a, #c89000);
  color:#3d2800;
  box-shadow:0 0 10px rgba(255,215,0,.25);
}
.medal-badge.prata{
  background:radial-gradient(circle at 35% 35%, #e8e8e8, #888);
  color:#2a2a2a;
  box-shadow:0 0 8px rgba(200,200,200,.15);
}
.medal-badge.bronze{
  background:radial-gradient(circle at 35% 35%, #e8a050, #804010);
  color:#2a1000;
  box-shadow:0 0 8px rgba(205,127,50,.2);
}
.medal-label{font-size:9px;font-weight:600}
.medal-rank{font-size:7px;opacity:.7;letter-spacing:.02em}

.entry-info{flex:1;min-width:0}
.beer-name{
  font-size:14px;
  font-weight:500;
  color:var(--cream);
  line-height:1.3;
  margin-bottom:3px;
}
.brewery-row{
  display:flex;align-items:center;gap:6px;flex-wrap:wrap;
}
.brewery-name{
  font-size:12px;
  color:#c0a878;
  font-family:'IBM Plex Mono',monospace;
  word-break:break-word;
  cursor:pointer;
  transition:color .15s;
  text-decoration:underline;
  text-decoration-color:rgba(192,168,120,.3);
  text-underline-offset:2px;
}
.brewery-name:hover{
  color:var(--amber);
  text-decoration-color:var(--amber-dim);
}
.state-tag{
  flex-shrink:0;
  font-family:'IBM Plex Mono',monospace;
  font-size:10px;
  font-weight:500;
  padding:2px 6px;
  border-radius:3px;
  background:var(--faint);
  color:var(--muted);
  letter-spacing:.05em;
}
.match-dot{
  flex-shrink:0;
  width:7px;height:7px;
  border-radius:50%;
  background:var(--match-text);
  display:none;
}
.is-match .match-dot{display:block}

/* ─── BREWERIES OVERLAY ──────────────────────────────── */
.overlay{
  position:fixed;inset:0;
  z-index:500;
  display:flex;
  align-items:stretch;
  justify-content:flex-end;
  background:rgba(0,0,0,.6);
  backdrop-filter:blur(3px);
  animation:fadeIn .2s ease;
}
.overlay.hidden{display:none}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}

.overlay-panel{
  width:min(700px, 100vw);
  background:var(--surface);
  border-left:1px solid var(--border);
  display:flex;
  flex-direction:column;
  overflow:hidden;
  animation:slideLeft .25s cubic-bezier(.2,.8,.3,1);
}
@keyframes slideLeft{
  from{transform:translateX(40px);opacity:0}
  to{transform:translateX(0);opacity:1}
}
.overlay-header{
  padding:18px 20px;
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:12px;
  flex-shrink:0;
}
.overlay-title{
  font-family:'Playfair Display',serif;
  font-size:20px;font-weight:700;
  color:var(--cream);
  flex:1;
}
.overlay-close{
  width:32px;height:32px;
  border-radius:50%;
  border:1px solid var(--border);
  background:transparent;
  color:var(--muted);
  font-size:18px;
  cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:all .15s;
  line-height:1;
}
.overlay-close:hover{background:var(--card);color:var(--cream)}

.overlay-body{
  overflow-y:auto;
  flex:1;
  padding:0;
}
.overlay-body::-webkit-scrollbar{width:5px}
.overlay-body::-webkit-scrollbar-track{background:transparent}
.overlay-body::-webkit-scrollbar-thumb{background:var(--faint);border-radius:3px}

.ov-section{
  border-bottom:1px solid var(--border);
}
.ov-section-title{
  padding:14px 20px;
  font-family:'IBM Plex Mono',monospace;
  font-size:11px;
  letter-spacing:.08em;
  text-transform:uppercase;
  font-weight:500;
  position:sticky;top:0;
  background:var(--surface);
  border-bottom:1px solid var(--border);
  z-index:10;
}
.ov-section-title.both{color:var(--match-text)}
.ov-section-title.only-a{color:var(--amber)}
.ov-section-title.only-b{color:var(--blue)}
.ov-section-title.only-c{color:var(--green)}

/* Brewery accordion in overlay */
.bw-item{
  border-bottom:1px solid rgba(46,34,16,.6);
}
.bw-item:last-child{border-bottom:none}
.bw-header{
  display:flex;align-items:center;
  padding:11px 20px;
  cursor:pointer;
  gap:10px;
  transition:background .15s;
}
.bw-header:hover{background:var(--card-hover)}
.bw-name{
  font-size:14px;
  font-weight:500;
  color:var(--cream);
  flex:1;
}
.bw-counts{
  font-family:'IBM Plex Mono',monospace;
  font-size:10px;
  color:var(--muted);
  display:flex;gap:8px;
}
.bw-count-a{color:var(--amber-dim)}
.bw-count-b{color:#4a7fa0}
.bw-count-c{color:var(--green-dim)}
.bw-count-single{color:var(--muted)}
.bw-chevron{
  color:var(--muted);font-size:10px;
  font-family:'IBM Plex Mono',monospace;
  transition:transform .2s;flex-shrink:0;
}
.bw-item.open .bw-chevron{transform:rotate(90deg)}
.bw-item.open .bw-header{background:var(--card)}

.bw-detail{
  display:none;
  padding:0 0 10px;
  background:var(--card);
  border-top:1px solid var(--border);
}
.bw-item.open .bw-detail{display:block}

.bw-comp-label{
  padding:8px 20px 4px;
  font-family:'IBM Plex Mono',monospace;
  font-size:9px;
  letter-spacing:.08em;
  text-transform:uppercase;
  font-weight:500;
}
.bw-comp-label.la{color:var(--amber-dim)}
.bw-comp-label.lb{color:#4a7fa0}
.bw-comp-label.lc{color:var(--green-dim)}
.bw-comp-label.lsingle{color:var(--muted)}

.bw-entry{
  display:flex;align-items:center;
  padding:5px 20px;
  gap:10px;
}
.bw-medal{
  flex-shrink:0;
  width:20px;height:20px;
  border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:8px;font-weight:700;
  font-family:'IBM Plex Mono',monospace;
}
.bw-medal.ouro{background:radial-gradient(circle at 35% 35%,#ffe55a,#c89000);color:#3d2800}
.bw-medal.prata{background:radial-gradient(circle at 35% 35%,#e8e8e8,#888);color:#2a2a2a}
.bw-medal.bronze{background:radial-gradient(circle at 35% 35%,#e8a050,#804010);color:#2a1000}
.bw-style{
  font-size:12px;color:var(--muted);
  flex:1;font-family:'IBM Plex Mono',monospace;
}
.bw-beer{
  font-size:12px;color:var(--cream);
  text-align:right;flex-shrink:0;max-width:45%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}

/* ─── BREWERY DETAIL MODAL ────────────────────────────────── */
.bw-modal{
  position:fixed;inset:0;
  z-index:600;
  display:flex;align-items:center;justify-content:center;
  background:rgba(0,0,0,.7);
  backdrop-filter:blur(4px);
  animation:fadeIn .2s ease;
  padding:16px;
}
.bw-modal.hidden{display:none}
.bw-modal-panel{
  width:min(560px,100%);
  max-height:90vh;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:12px;
  display:flex;flex-direction:column;
  overflow:hidden;
  animation:scaleUp .2s cubic-bezier(.2,.8,.3,1);
}
@keyframes scaleUp{
  from{opacity:0;transform:scale(.95)}
  to{opacity:1;transform:scale(1)}
}
.bw-modal-header{
  padding:18px 20px;
  border-bottom:1px solid var(--border);
  display:flex;align-items:flex-start;gap:12px;
  flex-shrink:0;
}
.bw-modal-name{
  font-family:'Playfair Display',serif;
  font-size:20px;font-weight:700;
  color:var(--cream);
  flex:1;
  line-height:1.3;
}
.bw-modal-body{
  overflow-y:auto;
  flex:1;
}
.bw-modal-body::-webkit-scrollbar{width:4px}
.bw-modal-body::-webkit-scrollbar-thumb{background:var(--faint);border-radius:2px}
.bw-modal-body::-webkit-scrollbar-thumb:hover{background:var(--amber-dim)}

.bw-modal-contest{
  padding:12px 20px 4px;
  border-top:1px solid var(--border);
}
.bw-modal-contest:first-child{border-top:none}
.bw-modal-contest-name{
  font-family:'IBM Plex Mono',monospace;
  font-size:10px;letter-spacing:.08em;text-transform:uppercase;
  font-weight:500;margin-bottom:8px;
}
.bw-modal-contest-name.ca{color:var(--amber)}
.bw-modal-contest-name.cb{color:var(--blue)}
.bw-modal-contest-name.cc{color:var(--green)}
.bw-modal-row{
  display:flex;align-items:center;
  padding:7px 0;
  gap:10px;
  border-bottom:1px solid rgba(46,34,16,.5);
}
.bw-modal-row:last-child{border-bottom:none}
.bw-modal-style{
  font-size:13px;color:var(--muted);
  flex:1;font-family:'IBM Plex Mono',monospace;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.bw-modal-beer{
  font-size:13px;font-weight:500;color:var(--cream);
  text-align:right;flex-shrink:0;max-width:48%;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}

/* ─── MOBILE ─────────────────────────────────────────────── */
@media(max-width:768px){
  :root{--sidebar-w:100%;--header-h:54px;--base-fs:15px}
  html,body{overflow:auto;height:auto}
  .app{flex-direction:column;height:auto;overflow:visible}
  .sidebar{
    width:100%;
    height:auto;
    border-right:none;
    border-bottom:2px solid var(--border);
    max-height:none;
  }
  .style-list{max-height:200px}
  .main{min-height:50vh}
  .comp-grid{grid-template-columns:1fr}
  .header-stats .stat-pill:not(.match){display:none}
  .header-subtitle{display:none}
  .ms-header{padding:13px 16px}
  .ms-detail{padding:12px 16px 16px}
  .overlay-panel{width:100vw;border-left:none}
}
@media(max-width:480px){
  .header-logo-img{height:24px}
  .year-btn{font-size:10px;padding:2px 7px}
  .ms-name{font-size:16px}
  .filter-bar{gap:4px}
  .filter-btn{font-size:10px;padding:3px 7px}
}
</style>
</head>
<body>

<header>
  <div class="header-brand">
    <img src="https://pint.network/assets/pint.network-BqzakIyD.png" alt="Pint.Network" class="header-logo-img">
    <div class="header-divider"></div>
    <span class="header-subtitle">Análise de Concursos Comerciais</span>
  </div>
  <nav class="header-nav">
    <a href="ranking.html" class="nav-link">Ranking</a>
    <a href="index.html" class="nav-link active">Medalhas</a>
  </nav>
  <div class="year-filter">
    ''' + ''.join(f'<button class="year-btn{" active" if y == DATA["years"][-1] else ""}" data-year="{y}">{y}</button>' for y in DATA['years']) + '''
  </div>
  <div class="header-stats">
    <div class="stat-pill cbc-a" id="stat-cbc"></div>
    <div class="stat-pill cbc-b" id="stat-blu"></div>
    <div class="stat-pill cbc-c" id="stat-bbc"></div>
    <div class="stat-pill match" id="btn-breweries" title="Ver cervejarias em múltiplos concursos"></div>
  </div>
</header>

<div class="app">
  <aside class="sidebar">
    <div class="search-wrap">
      <input class="search-input" type="text" id="search" placeholder="Buscar estilo..." autocomplete="off">
    </div>
    <div class="filter-bar">
      <button class="filter-btn active" data-filter="all">Todos</button>
      <button class="filter-btn" data-filter="multi">Múltiplos</button>
      <button class="filter-btn" data-filter="cbc">CBC</button>
      <button class="filter-btn" data-filter="blumenau">Blumenau</button>
      <button class="filter-btn" data-filter="bbc">BBC</button>
      <button class="filter-btn" data-filter="match">◆ Match</button>
    </div>
    <div class="style-count" id="style-count"></div>
    <div class="style-list" id="style-list"></div>
  </aside>

  <main class="main" id="main">
    <div id="main-style-list"></div>
  </main>
</div>

<!-- Breweries Overlay -->
<div class="overlay hidden" id="overlay">
  <div class="overlay-panel">
    <div class="overlay-header">
      <span class="overlay-title">Cervejarias nos Concursos</span>
      <button class="overlay-close" id="overlay-close" aria-label="Fechar">×</button>
    </div>
    <div class="overlay-body" id="overlay-body"></div>
  </div>
</div>

<!-- Brewery Detail Modal -->
<div class="bw-modal hidden" id="bw-modal">
  <div class="bw-modal-panel">
    <div class="bw-modal-header">
      <span class="bw-modal-name" id="bw-modal-name"></span>
      <button class="overlay-close" id="bw-modal-close" aria-label="Fechar">×</button>
    </div>
    <div class="bw-modal-body" id="bw-modal-body"></div>
  </div>
</div>

<script>
const RESULTS_DATA     = ''' + RJ  + ''';
const BREWERY_DATA_ALL = ''' + BDJ + ''';
const STATS_ALL        = ''' + STJ + ''';
const CONTESTS_BY_YEAR = ''' + CBJ + ''';

const COMP_A = RESULTS_DATA.contests.cbc;
const COMP_B = RESULTS_DATA.contests.blumenau;
const COMP_C = RESULTS_DATA.contests.bbc;

const CONTEST_LABELS = {cbc: COMP_A, blumenau: COMP_B, bbc: COMP_C};
const CONTEST_CARD   = {cbc: 'comp-a', blumenau: 'comp-b', bbc: 'comp-c'};
const CONTEST_DOT    = {cbc: 'a', blumenau: 'b', bbc: 'c'};
const CONTEST_ABBR   = {cbc: 'CBC', blumenau: 'BLU', bbc: 'BBC'};
const CONTEST_LABEL_CLS = {cbc: 'la', blumenau: 'lb', bbc: 'lc'};
const CONTEST_MODAL_CLS = {cbc: 'ca', blumenau: 'cb', bbc: 'cc'};
const CONTEST_COUNT_CLS = {cbc: 'bw-count-a', blumenau: 'bw-count-b', bbc: 'bw-count-c'};

const MEDAL_PT = {Ouro:'OURO', Prata:'PRATA', Bronze:'BRONZE'};
const MEDAL_ORDER = {Ouro:0, Prata:1, Bronze:2};

let currentStyle  = null;
let currentFilter = 'all';
let currentYear   = RESULTS_DATA.years[RESULTS_DATA.years.length - 1];

function getActiveContests() {
  return CONTESTS_BY_YEAR[currentYear] || ['cbc', 'blumenau'];
}

function getBD() { return BREWERY_DATA_ALL[currentYear] || {multi:[],onlyCbc:[],onlyBlu:[],onlyBbc:[]}; }

function updateStats() {
  const s      = STATS_ALL[currentYear] || {};
  const active = getActiveContests();

  document.getElementById('stat-cbc').innerHTML = '<b>' + (s.stylesCbc||0) + '</b>&nbsp;estilos · CBC';
  document.getElementById('stat-blu').innerHTML = '<b>' + (s.stylesBlu||0) + '</b>&nbsp;estilos · Blumenau';

  const bbcPill = document.getElementById('stat-bbc');
  bbcPill.innerHTML = '<b>' + (s.stylesBbc||0) + '</b>&nbsp;estilos · BBC';
  bbcPill.style.display = active.includes('bbc') ? '' : 'none';

  document.getElementById('btn-breweries').innerHTML =
    '◆&nbsp;<b>' + (s.multi||0) + '</b>&nbsp;cervejarias em múltiplos';
}

function getEntries(d, contest) {
  const cd = d[contest];
  if (!cd) return [];
  return cd[currentYear] || [];
}

// Compute shared-brewery styles for current year
let matchStyles = new Set();
function recomputeMatchStyles() {
  matchStyles = new Set();
  const active = getActiveContests();
  if (active.length < 2) return;
  for (const s of RESULTS_DATA.styles) {
    const d = RESULTS_DATA.data[s];
    const sets = active.map(c => new Set(getEntries(d, c).map(e => e.brewery.toLowerCase())));
    const hasMatch = sets.some((setA, i) =>
      sets.slice(i + 1).some(setB => [...setA].some(b => setB.has(b)))
    );
    if (hasMatch) matchStyles.add(s);
  }
}
recomputeMatchStyles();

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function sharedBreweries(style) {
  const d      = RESULTS_DATA.data[style];
  const active = getActiveContests();
  const sets   = active.map(c => new Set(getEntries(d, c).map(e => e.brewery.toLowerCase())));
  const shared = new Set();
  for (let i = 0; i < sets.length; i++) {
    for (let j = i + 1; j < sets.length; j++) {
      for (const b of sets[i]) { if (sets[j].has(b)) shared.add(b); }
    }
  }
  return shared;
}

function styleSlug(s) { return s.replace(/[^a-zA-Z0-9]/g, '_'); }

// ─── SIDEBAR ────────────────────────────────────────────────
function renderSidebar(query, filter) {
  const list  = document.getElementById('style-list');
  const count = document.getElementById('style-count');
  const q      = query.toLowerCase().trim();
  const active = getActiveContests();

  const filtered = RESULTS_DATA.styles.filter(s => {
    const d      = RESULTS_DATA.data[s];
    const hasAny = active.some(c => getEntries(d, c).length > 0);
    if (!hasAny) return false;
    if (q && !s.toLowerCase().includes(q)) return false;
    if (filter === 'multi')    { return active.filter(c => getEntries(d,c).length>0).length >= 2; }
    if (filter === 'cbc')      return getEntries(d,'cbc').length > 0;
    if (filter === 'blumenau') return getEntries(d,'blumenau').length > 0;
    if (filter === 'bbc')      return getEntries(d,'bbc').length > 0;
    if (filter === 'match')    return matchStyles.has(s);
    return true;
  });

  count.textContent = `${filtered.length} estilo${filtered.length !== 1 ? 's' : ''}`;

  list.innerHTML = filtered.map(s => {
    const d       = RESULTS_DATA.data[s];
    const isMatch = matchStyles.has(s);
    const isActive = s === currentStyle;
    const dots = active.map(c => {
      const has = getEntries(d, c).length > 0;
      return `<span class="dot${has ? ' ' + CONTEST_DOT[c] : ''}" title="${esc(CONTEST_LABELS[c])}"></span>`;
    }).join('');
    return `<div class="style-item${isActive ? ' active' : ''}${isMatch ? ' match-style' : ''}" data-style="${esc(s)}">
      <span class="style-name">${esc(s)}</span>
      <span class="style-dots">${dots}</span>
    </div>`;
  }).join('');

  list.querySelectorAll('.style-item').forEach(el => {
    el.addEventListener('click', () => selectStyle(el.dataset.style, 'sidebar'));
  });
}

// ─── MEDAL CARD ──────────────────────────────────────────────
function renderMedalCard(entries, compClass, compLabel, sharedSet) {
  if (!entries || entries.length === 0) {
    return `<div class="comp-card ${compClass}">
      <div class="comp-header"><span class="comp-name">${esc(compLabel)}</span></div>
      <div class="comp-no-data">Sem medalhas neste estilo</div>
    </div>`;
  }
  const rows = entries.map(e => {
    const isMatch = sharedSet.has(e.brewery.toLowerCase());
    const medalClass = e.medal.toLowerCase();
    return `<div class="medal-entry${isMatch ? ' is-match' : ''}">
      <div class="medal-badge ${medalClass}">
        <span class="medal-label">${MEDAL_PT[e.medal] || e.medal.toUpperCase()}</span>
      </div>
      <div class="entry-info">
        <div class="beer-name">${esc(e.beer)}</div>
        <div class="brewery-row">
          <span class="brewery-name" title="${esc(e.brewery)}" data-brewery="${esc(e.brewery)}">${esc(e.brewery)}</span>
          <span class="state-tag">${esc(e.state)}</span>
          <span class="match-dot" title="Cervejaria vencedora em múltiplos concursos"></span>
        </div>
      </div>
    </div>`;
  }).join('');
  return `<div class="comp-card ${compClass}">
    <div class="comp-header"><span class="comp-name">${esc(compLabel)}</span></div>
    ${rows}
  </div>`;
}

function renderComparisonDetail(style) {
  const d      = RESULTS_DATA.data[style];
  const shared = sharedBreweries(style);
  const active = getActiveContests();
  const matchHtml = shared.size > 0
    ? `<div class="match-badge visible"><span>◆</span> Mesma cervejaria vencedora em múltiplos concursos</div>`
    : '';
  const cards = active.map(c =>
    renderMedalCard(getEntries(d, c), CONTEST_CARD[c], CONTEST_LABELS[c], shared)
  ).join('');
  return `${matchHtml}<div class="comp-grid">${cards}</div>`;
}

// ─── MAIN ACCORDION ──────────────────────────────────────────
function renderMainList(query, filter) {
  const q      = query.toLowerCase().trim();
  const active = getActiveContests();

  const filtered = RESULTS_DATA.styles.filter(s => {
    const d      = RESULTS_DATA.data[s];
    const hasAny = active.some(c => getEntries(d, c).length > 0);
    if (!hasAny) return false;
    if (q && !s.toLowerCase().includes(q)) return false;
    if (filter === 'multi')    { return active.filter(c => getEntries(d,c).length>0).length >= 2; }
    if (filter === 'cbc')      return getEntries(d,'cbc').length > 0;
    if (filter === 'blumenau') return getEntries(d,'blumenau').length > 0;
    if (filter === 'bbc')      return getEntries(d,'bbc').length > 0;
    if (filter === 'match')    return matchStyles.has(s);
    return true;
  });

  const container = document.getElementById('main-style-list');
  container.innerHTML = filtered.map(s => {
    const d       = RESULTS_DATA.data[s];
    const isMatch = matchStyles.has(s);
    const isActive = s === currentStyle;
    const slug    = styleSlug(s);
    const dots = active.map(c => {
      const has = getEntries(d, c).length > 0;
      return `<span class="dot${has ? ' ' + CONTEST_DOT[c] : ''}" title="${esc(CONTEST_LABELS[c])}"></span>`;
    }).join('');
    const detailHtml = `<div class="ms-detail">${renderComparisonDetail(s)}</div>`;
    return `<div class="ms-item active${isActive ? ' selected' : ''}" id="ms-${slug}" data-style="${esc(s)}">
      <div class="ms-header">
        <span class="ms-name">${esc(s)}</span>
        <span class="ms-dots">${dots}</span>
        ${isMatch ? '<span class="ms-match-tag">◆ match</span>' : ''}
        <span class="ms-chevron">&#9658;</span>
      </div>
      ${detailHtml}
    </div>`;
  }).join('');

  container.querySelectorAll('.ms-item').forEach(el => {
    el.querySelector('.ms-header').addEventListener('click', () => selectStyle(el.dataset.style, 'main'));
  });
}

// ─── SELECT STYLE ────────────────────────────────────────────
function selectStyle(style, source) {
  currentStyle = style;
  renderSidebar(document.getElementById('search').value, currentFilter);
  document.querySelectorAll('.ms-item.selected').forEach(el => el.classList.remove('selected'));
  const slug = styleSlug(style);
  const el   = document.getElementById('ms-' + slug);
  if (el) {
    el.classList.add('selected');
    setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 30);
  }
  if (source !== 'sidebar') {
    const sidebarEl = document.querySelector('.style-item.active');
    if (sidebarEl) sidebarEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// ─── BREWERIES OVERLAY ───────────────────────────────────────
function renderBreweriesOverlay() {
  const bd     = getBD();
  const body   = document.getElementById('overlay-body');
  const active = getActiveContests();

  function medalHtml(m) {
    return `<span class="bw-medal ${m.toLowerCase()}">${m[0]}</span>`;
  }

  function multiBreweryHtml(b) {
    const inConts = active.filter(c => (b[c]||[]).length > 0);
    const counts = inConts.map(c =>
      `<span class="${CONTEST_COUNT_CLS[c]}">${b[c].length} ${CONTEST_ABBR[c]}</span>`
    ).join('');
    let detail = '';
    for (const c of inConts) {
      detail += `<div class="bw-comp-label ${CONTEST_LABEL_CLS[c]}">${esc(CONTEST_LABELS[c])}</div>`;
      for (const e of b[c]) {
        detail += `<div class="bw-entry">${medalHtml(e.medal)}<span class="bw-style">${esc(e.style)}</span><span class="bw-beer">${esc(e.beer)}</span></div>`;
      }
    }
    return `<div class="bw-item">
      <div class="bw-header">
        <span class="bw-name">${esc(b.name)}</span>
        <span class="bw-counts">${counts}</span>
        <span class="bw-chevron">&#9658;</span>
      </div>
      <div class="bw-detail">${detail}</div>
    </div>`;
  }

  function singleBreweryHtml(b, contest) {
    const n = b.entries.length;
    const counts = `<span class="bw-count-single">${n} medalha${n>1?'s':''}</span>`;
    let detail = `<div class="bw-comp-label ${CONTEST_LABEL_CLS[contest]}">${esc(CONTEST_LABELS[contest])}</div>`;
    for (const e of b.entries) {
      detail += `<div class="bw-entry">${medalHtml(e.medal)}<span class="bw-style">${esc(e.style)}</span><span class="bw-beer">${esc(e.beer)}</span></div>`;
    }
    return `<div class="bw-item">
      <div class="bw-header">
        <span class="bw-name">${esc(b.name)}</span>
        <span class="bw-counts">${counts}</span>
        <span class="bw-chevron">&#9658;</span>
      </div>
      <div class="bw-detail">${detail}</div>
    </div>`;
  }

  let html = `<div class="ov-section">
    <div class="ov-section-title both">◆ Em Múltiplos Concursos (${bd.multi.length})</div>`;
  for (const b of bd.multi) html += multiBreweryHtml(b);
  html += '</div>';

  const singleSections = [
    {key:'onlyCbc', contest:'cbc',      title:'Somente CBC — Concurso Brasileiro', cls:'only-a'},
    {key:'onlyBlu', contest:'blumenau', title:'Somente Concurso Brasileiro de Blumenau',  cls:'only-b'},
    {key:'onlyBbc', contest:'bbc',      title:'Somente Brasil Beer Cup',           cls:'only-c'},
  ];
  for (const {key, contest, title, cls} of singleSections) {
    if (!active.includes(contest)) continue;
    const section = bd[key] || [];
    html += `<div class="ov-section">
      <div class="ov-section-title ${cls}">${title} (${section.length})</div>`;
    for (const b of section) html += singleBreweryHtml(b, contest);
    html += '</div>';
  }

  body.innerHTML = html;
  body.querySelectorAll('.bw-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.bw-item').classList.toggle('open'));
  });
}

function openOverlay() {
  document.getElementById('overlay').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  renderBreweriesOverlay();
}
function closeOverlay() {
  document.getElementById('overlay').classList.add('hidden');
  document.body.style.overflow = '';
}

// ─── EVENT LISTENERS ─────────────────────────────────────────
document.getElementById('search').addEventListener('input', e => {
  renderSidebar(e.target.value, currentFilter);
  renderMainList(e.target.value, currentFilter);
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderSidebar(document.getElementById('search').value, currentFilter);
    renderMainList(document.getElementById('search').value, currentFilter);
  });
});

document.getElementById('btn-breweries').addEventListener('click', openOverlay);
document.getElementById('overlay-close').addEventListener('click', closeOverlay);
document.getElementById('overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('overlay')) closeOverlay();
});

// Year filter
document.querySelectorAll('.year-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.year-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentYear  = btn.dataset.year;
    currentStyle = null;
    // Reset filter if the selected contest is not active this year
    const active = getActiveContests();
    if (!['all','multi','match'].includes(currentFilter) && !active.includes(currentFilter)) {
      currentFilter = 'all';
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('.filter-btn[data-filter="all"]').classList.add('active');
    }
    recomputeMatchStyles();
    rebuildBreweryLookup();
    updateStats();
    renderSidebar(document.getElementById('search').value, currentFilter);
    renderMainList(document.getElementById('search').value, currentFilter);
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeBreweryModal(); closeOverlay(); }
});

// ─── BREWERY DETAIL ──────────────────────────────────────────
let BREWERY_LOOKUP = {};

function rebuildBreweryLookup() {
  BREWERY_LOOKUP = {};
  for (const [style, contests] of Object.entries(RESULTS_DATA.data)) {
    for (const c of Object.keys(contests)) {
      const entries = (contests[c]||{})[currentYear] || [];
      for (const e of entries) {
        const k = e.brewery.toLowerCase();
        if (!BREWERY_LOOKUP[k]) BREWERY_LOOKUP[k] = {name: e.brewery, cbc:[], blumenau:[], bbc:[]};
        if (BREWERY_LOOKUP[k][c]) {
          BREWERY_LOOKUP[k][c].push({style, medal: e.medal, beer: e.beer, state: e.state||''});
        }
      }
    }
  }
  // Sort entries within each contest by style then medal
  for (const info of Object.values(BREWERY_LOOKUP)) {
    for (const c of ['cbc','blumenau','bbc']) {
      info[c].sort((a,b) => a.style.localeCompare(b.style) || (MEDAL_ORDER[a.medal]||9) - (MEDAL_ORDER[b.medal]||9));
    }
  }
}
rebuildBreweryLookup();

function showBreweryDetail(name) {
  const info = BREWERY_LOOKUP[name.toLowerCase()];
  if (!info) return;

  document.getElementById('bw-modal-name').textContent = info.name;

  let html = '';
  for (const c of getActiveContests()) {
    const entries = info[c] || [];
    if (!entries.length) continue;
    const rows = entries.map(e => `
      <div class="bw-modal-row">
        <div class="medal-badge ${e.medal.toLowerCase()}" style="width:28px;height:28px;font-size:7px;flex-shrink:0">
          <span class="medal-label" style="font-size:7px">${MEDAL_PT[e.medal]||e.medal}</span>
        </div>
        <span class="bw-modal-style" title="${esc(e.style)}">${esc(e.style)}</span>
        <span class="bw-modal-beer"  title="${esc(e.beer)}">${esc(e.beer)}</span>
      </div>`).join('');
    html += `<div class="bw-modal-contest">
      <div class="bw-modal-contest-name ${CONTEST_MODAL_CLS[c]}">${esc(CONTEST_LABELS[c])}</div>
      ${rows}
    </div>`;
  }

  document.getElementById('bw-modal-body').innerHTML = html;
  document.getElementById('bw-modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeBreweryModal() {
  document.getElementById('bw-modal').classList.add('hidden');
  document.body.style.overflow = '';
}

document.getElementById('bw-modal-close').addEventListener('click', closeBreweryModal);
document.getElementById('bw-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('bw-modal')) closeBreweryModal();
});

// Event delegation for brewery name clicks
document.addEventListener('click', e => {
  if (e.target.classList.contains('brewery-name')) {
    e.stopPropagation();
    showBreweryDetail(e.target.dataset.brewery || e.target.textContent.trim());
  }
});

// ─── INIT ────────────────────────────────────────────────────
updateStats();
renderSidebar('', 'all');
renderMainList('', 'all');
</script>
</body>
</html>'''

with open(BASE + 'index.html', 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f'index.html written ({len(HTML)//1024}KB)')
for year in DATA['years']:
    s  = STATS_BY_YEAR[year]
    bd = BREWERY_DATA_BY_YEAR[year]
    active = CONTESTS_BY_YEAR[year]
    print(f'  {year} [{", ".join(active)}]: CBC {s["stylesCbc"]} / Blumenau {s["stylesBlu"]} / BBC {s["stylesBbc"]} styles | {s["multi"]} breweries in multiple')
