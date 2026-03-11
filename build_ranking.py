#!/usr/bin/env python3
"""Build index.html from results.json.

Scoring: Ouro = 3 pts, Prata = 2 pts, Bronze = 1 pt

Sections:
  1.  Top 10 Cervejarias           (per year + all)
  2.  Especialistas em Ouro        (gold ratio, per year + all)
  3.  Consistência entre Anos      (all-year view only)
  4.  Maior Evolução               (all-year view only)
  5.  Diversidade de Estilos       (per year + all)
  6.  Top 10 por Estado            (per year + all)
  7.  Ranking de Estados           (per year + all)
  8.  Estilo Dominante por Estado  (per year + all)
  9.  Dominância por Estilo        (per year + all)
  10. Estilos Mais Disputados      (per year + all)
  11. Estilos Menos Premiados      (per year + all)
"""
import json
from collections import defaultdict
from pathlib import Path

BASE = Path('/Users/hboavent/Projects/personal/concursos-resultados/')

with open(BASE / 'results.json', 'r', encoding='utf-8') as f:
    DATA = json.load(f)

MEDAL_POINTS = {'Ouro': 3, 'Prata': 2, 'Bronze': 1}

ALL_STATES = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF',
    'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
    'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS',
    'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]

CONTEST_ORDER = ('cbc', 'blumenau', 'bbc', 'abracerva')


def _strip(b):
    """Return brewery dict without heavy 'entries' field."""
    return {k: v for k, v in b.items() if k != 'entries'}


def compute_ranking_data(years):
    brewery_stats    = {}
    style_medal_cnt  = defaultdict(lambda: {'ouro': 0, 'prata': 0, 'bronze': 0, 'total': 0, 'winners': set()})
    style_brew_stats = defaultdict(lambda: defaultdict(lambda: {'display': '', 'state': '', 'points': 0, 'ouro': 0, 'prata': 0, 'bronze': 0}))
    state_style_cnt  = defaultdict(lambda: defaultdict(lambda: {'ouro': 0, 'prata': 0, 'bronze': 0, 'total': 0}))

    for style, cd in DATA['data'].items():
        for contest in CONTEST_ORDER:
            for year in years:
                for e in cd.get(contest, {}).get(year, []):
                    bl       = e['brewery'].lower()
                    pts      = MEDAL_POINTS.get(e['medal'], 0)
                    medal_lc = e['medal'].lower()
                    st       = e.get('state', '')

                    # ── Brewery aggregate ─────────────────────────
                    if bl not in brewery_stats:
                        brewery_stats[bl] = {
                            'display': e['brewery'], 'state': st,
                            'points': 0, 'ouro': 0, 'prata': 0, 'bronze': 0,
                            'contests': set(), 'styles': set(),
                        }
                    b = brewery_stats[bl]
                    b['points']  += pts
                    b[medal_lc]  += 1
                    b['contests'].add(contest)
                    b['styles'].add(style)
                    b.setdefault('entries', []).append({'beer': e.get('beer',''), 'style': style, 'contest': contest, 'year': year, 'medal': e['medal']})

                    # ── Style medal tally ─────────────────────────
                    sc = style_medal_cnt[style]
                    sc[medal_lc] += 1
                    sc['total']  += 1
                    sc['winners'].add(bl)

                    # ── Per-style per-brewery (dominance) ─────────
                    sb = style_brew_stats[style][bl]
                    if not sb['display']:
                        sb['display'] = e['brewery']
                        sb['state']   = st
                    sb['points']  += pts
                    sb[medal_lc]  += 1

                    # ── State × style ─────────────────────────────
                    if st in ALL_STATES:
                        ss = state_style_cnt[st][style]
                        ss[medal_lc] += 1
                        ss['total']  += 1

    # ── Serialise breweries ───────────────────────────────────────
    all_breweries = []
    for bl, b in brewery_stats.items():
        b['n_styles']   = len(b['styles'])
        b['n_contests'] = len(b['contests'])
        b['n_medals']   = b['ouro'] + b['prata'] + b['bronze']
        b['gold_ratio'] = round(b['ouro'] / b['n_medals'] * 100) if b['n_medals'] else 0
        b['contests']   = sorted(b['contests'], key=lambda c: CONTEST_ORDER.index(c) if c in CONTEST_ORDER else 99)
        del b['styles']
        all_breweries.append(b)

    all_breweries.sort(key=lambda x: (-x['points'], -x['ouro'], -x['prata'], x['display'].lower()))
    for i, b in enumerate(all_breweries):
        b['rank'] = i + 1

    def _group_entries(entries):
        result = {}
        for en in entries:
            c = en['contest']; y = en['year']
            if c not in result: result[c] = {}
            if y not in result[c]: result[c][y] = []
            result[c][y].append({'beer': en['beer'], 'style': en['style'], 'medal': en['medal']})
        return result

    for b in all_breweries:
        b['medal_entries'] = _group_entries(b.get('entries', []))
        if 'entries' in b:
            del b['entries']

    # ── Top 10 overall ────────────────────────────────────────────
    top10_overall = [_strip(b) for b in all_breweries[:10]]

    # ── State map ─────────────────────────────────────────────────
    state_map = defaultdict(list)
    for b in all_breweries:
        st = b['state'] if b['state'] in ALL_STATES else ('?' if not b['state'] else b['state'])
        state_map[st].append(b)

    top10_by_state = {}
    for st in ALL_STATES:
        bws = state_map.get(st, [])
        top10_by_state[st] = [dict(_strip(b), state_rank=i + 1) for i, b in enumerate(bws[:10])]
    if '?' in state_map:
        top10_by_state['?'] = [dict(_strip(b), state_rank=i + 1) for i, b in enumerate(state_map['?'][:10])]

    # ── State totals (all 27 UFs) ─────────────────────────────────
    state_totals = []
    for st in ALL_STATES:
        bws = state_map.get(st, [])
        state_totals.append({
            'state':     st,
            'points':    sum(b['points'] for b in bws),
            'ouro':      sum(b['ouro']   for b in bws),
            'prata':     sum(b['prata']  for b in bws),
            'bronze':    sum(b['bronze'] for b in bws),
            'breweries': len(bws),
        })
    state_totals.sort(key=lambda x: (-x['points'], -x['ouro'], x['state']))

    # ── Diversity top 10 ──────────────────────────────────────────
    diversity_top10 = [_strip(b) for b in sorted(
        all_breweries, key=lambda x: (-x['n_styles'], -x['points'], x['display'].lower())
    )[:10]]

    # ── Gold specialists (min 3 medals, top 10 by gold_ratio) ─────
    gold_specialists = sorted(
        [_strip(b) for b in all_breweries if b['n_medals'] >= 3],
        key=lambda x: (-x['gold_ratio'], -x['points'])
    )[:10]

    # ── Style dominance (top 25 by dominant brewery pts) ──────────
    style_dominance_all = []
    for style, brew_map in style_brew_stats.items():
        if not brew_map:
            continue
        top_b  = max(brew_map.values(), key=lambda x: x['points'])
        sc     = style_medal_cnt[style]
        style_dominance_all.append({
            'style':            style,
            'brewery':          top_b['display'],
            'state':            top_b['state'],
            'points':           top_b['points'],
            'ouro':             top_b['ouro'],
            'prata':            top_b['prata'],
            'bronze':           top_b['bronze'],
            'total_medals':     sc['total'],
            'unique_breweries': len(sc['winners']),
        })
    style_dominance_all.sort(key=lambda x: (-x['points'], x['style']))
    style_dominance = style_dominance_all[:25]

    # ── Most contested styles (top 25 by unique winners) ──────────
    styles_most_contested = sorted(
        style_dominance_all,
        key=lambda x: (-x['unique_breweries'], -x['total_medals'])
    )[:25]

    # ── Fewest medals (top 25) ────────────────────────────────────
    style_list = [
        {'style': s, 'ouro': c['ouro'], 'prata': c['prata'], 'bronze': c['bronze'], 'total': c['total']}
        for s, c in style_medal_cnt.items() if c['total'] > 0
    ]
    style_list.sort(key=lambda x: (x['total'], x['style'].lower()))
    styles_least_medals = style_list[:25]

    # ── State dominant style ──────────────────────────────────────
    state_dominant_style = {}
    for st in ALL_STATES:
        styles = state_style_cnt.get(st, {})
        if not styles:
            state_dominant_style[st] = None
        else:
            best_style, best_counts = max(styles.items(), key=lambda x: (x[1]['total'], x[1]['ouro']))
            state_dominant_style[st] = {
                'style':  best_style,
                'total':  best_counts['total'],
                'ouro':   best_counts['ouro'],
                'prata':  best_counts['prata'],
                'bronze': best_counts['bronze'],
            }

    # ── Medal concentration ───────────────────────────────────────
    total_pts    = sum(b['points']   for b in all_breweries) or 1
    top10_pts    = sum(b['points']   for b in all_breweries[:10])
    total_medals = sum(b['n_medals'] for b in all_breweries) or 1
    top10_medals = sum(b['n_medals'] for b in all_breweries[:10])
    medal_concentration = {
        'pts_pct':    round(top10_pts    / total_pts    * 100),
        'medal_pct':  round(top10_medals / total_medals * 100),
        'total_pts':  total_pts,
        'total_medals': total_medals,
    }

    # ── Active contests ───────────────────────────────────────────
    active_contests = [
        c for c in CONTEST_ORDER
        if any(DATA['data'][s].get(c, {}).get(y) for s in DATA['styles'] for y in years)
    ]
    states_with_data = {st for st in ALL_STATES if state_map.get(st)}

    return {
        'top10_overall':        top10_overall,
        'top10_by_state':       top10_by_state,
        'state_totals':         state_totals,
        'diversity_top10':      diversity_top10,
        'gold_specialists':     gold_specialists,
        'style_dominance':      style_dominance,
        'styles_most_contested': styles_most_contested,
        'styles_least_medals':  styles_least_medals,
        'state_dominant_style': state_dominant_style,
        'medal_concentration':  medal_concentration,
        'total_breweries':      len(all_breweries),
        'active_contests':      active_contests,
        'states_with_data':     sorted(states_with_data),
    }


def compute_cross_year():
    """Consistency and evolution metrics across all individual years."""
    individual_years = DATA['years']

    brewery_yr = {}  # bl -> {display, state, pts_by_year}
    for year in individual_years:
        for style, cd in DATA['data'].items():
            for contest in CONTEST_ORDER:
                for e in cd.get(contest, {}).get(year, []):
                    bl  = e['brewery'].lower()
                    pts = MEDAL_POINTS.get(e['medal'], 0)
                    if bl not in brewery_yr:
                        brewery_yr[bl] = {
                            'display': e['brewery'],
                            'state':   e.get('state', ''),
                            'pts_by_year': {},
                        }
                    brewery_yr[bl]['pts_by_year'].setdefault(year, 0)
                    brewery_yr[bl]['pts_by_year'][year] += pts

    # Consistency: present in every individual year
    consistent = [
        b for b in brewery_yr.values()
        if set(b['pts_by_year'].keys()) == set(individual_years)
    ]
    for b in consistent:
        b['total_pts'] = sum(b['pts_by_year'].values())
    consistent.sort(key=lambda x: (-x['total_pts'], x['display'].lower()))

    # Evolution: compare last two years
    if len(individual_years) >= 2:
        y0, y1 = individual_years[-2], individual_years[-1]
        evolutions = []
        for b in brewery_yr.values():
            if y0 in b['pts_by_year'] and y1 in b['pts_by_year']:
                delta = b['pts_by_year'][y1] - b['pts_by_year'][y0]
                evolutions.append({
                    'display':   b['display'],
                    'state':     b['state'],
                    'prev_pts':  b['pts_by_year'][y0],
                    'curr_pts':  b['pts_by_year'][y1],
                    'delta':     delta,
                })
        evolutions.sort(key=lambda x: x['delta'])
        gains   = list(reversed(evolutions[-10:]))
        losses  = evolutions[:10]
        py, cy  = y0, y1
    else:
        gains = losses = []
        py = cy = individual_years[0] if individual_years else ''

    return {
        'consistency': consistent[:25],
        'evolution':   {'gains': gains, 'losses': losses, 'prev_year': py, 'curr_year': cy},
        'years':       individual_years,
    }


RANKING_BY_YEAR              = {year: compute_ranking_data([year]) for year in DATA['years']}
RANKING_BY_YEAR['all']       = compute_ranking_data(DATA['years'])
CROSS_YEAR                   = compute_cross_year()

RKJ      = json.dumps(RANKING_BY_YEAR, ensure_ascii=False, separators=(',', ':'))
CYJ      = json.dumps(CROSS_YEAR,      ensure_ascii=False, separators=(',', ':'))
YEARS_J  = json.dumps(DATA['years'],   ensure_ascii=False, separators=(',', ':'))
STATES_J = json.dumps(ALL_STATES,      ensure_ascii=False, separators=(',', ':'))

# ─── HTML ──────────────────────────────────────────────────────────────────────

HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pint.Network — Ranking de Cervejarias</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0d0d;--surface:#141414;--card:#1c1c1c;--card-hover:#232323;
  --border:#2d2d2d;--amber:#f5c230;--amber-dim:#c49a20;--cream:#f0f0f0;
  --muted:#787878;--faint:#2a2a2a;--gold:#ffd700;--silver:#c8c8c8;--bronze:#cd7f32;
  --green:#4caf78;--green-dim:#2e7a50;--red:#e05555;--red-dim:#a03030;
  --header-h:60px;--content-w:1100px;
}
html,body{min-height:100%;background:var(--bg);color:var(--cream);font-family:'DM Sans',sans-serif;font-size:15px}

/* ─── HEADER ──────────────────────────────────────────────── */
header{position:fixed;top:0;left:0;right:0;height:var(--header-h);background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 18px;gap:14px;z-index:200}
.header-brand{display:flex;align-items:center;gap:12px;flex-shrink:0}
.header-logo-img{height:30px;width:auto;display:block}
.header-divider{width:1px;height:20px;background:var(--border);flex-shrink:0}
.header-subtitle{font-family:'DM Sans',sans-serif;font-size:12px;color:var(--muted);white-space:nowrap}
.header-nav{display:flex;gap:2px;margin-left:4px}
.nav-link{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;padding:3px 11px;border-radius:12px;border:1px solid var(--border);color:var(--muted);text-decoration:none;cursor:pointer;transition:all .15s;letter-spacing:.03em}
.nav-link:hover{border-color:var(--amber-dim);color:var(--amber)}
.nav-link.active{background:var(--amber);color:var(--bg);border-color:var(--amber)}
.year-filter{display:flex;gap:4px;margin-left:4px}
.year-btn{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;padding:3px 9px;border-radius:12px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;transition:all .15s;letter-spacing:.03em}
.year-btn.active{background:var(--amber);color:var(--bg);border-color:var(--amber)}
.header-right{display:flex;gap:10px;margin-left:auto;align-items:center}
.scoring-legend{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.04em;display:flex;gap:8px}
.s-ouro{color:var(--gold)}.s-prata{color:var(--silver)}.s-bronze{color:var(--bronze)}

/* ─── LAYOUT ──────────────────────────────────────────────── */
.ranking-main{max-width:var(--content-w);margin:0 auto;padding:calc(var(--header-h) + 28px) 20px 60px}
.ranking-section{margin-bottom:52px}
.section-header{display:flex;align-items:baseline;gap:14px;margin-bottom:8px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.section-title{font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:var(--cream)}
.section-desc{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);letter-spacing:.03em}
.section-count{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted)}
.section-only-all{display:none}

/* ─── CONCENTRATION BAR ───────────────────────────────────── */
.concentration-stats{
  display:flex;gap:20px;margin-bottom:14px;
  font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);
  align-items:center;
}
.conc-item b{color:var(--amber)}
.conc-bar-wrap{flex:1;height:4px;background:var(--faint);border-radius:2px;overflow:hidden;max-width:200px}
.conc-bar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--amber-dim),var(--amber))}

/* ─── RANK CARD ───────────────────────────────────────────── */
.rank-list{display:flex;flex-direction:column;gap:6px}
.rank-card{display:flex;align-items:center;gap:14px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;transition:background .15s,border-color .15s}
.rank-card:hover{background:var(--card-hover);border-color:#3d3d3d}
.rank-card.top1{border-color:rgba(255,215,0,.35);background:rgba(255,215,0,.04)}
.rank-card.top2{border-color:rgba(200,200,200,.25);background:rgba(200,200,200,.02)}
.rank-card.top3{border-color:rgba(205,127,50,.3);background:rgba(205,127,50,.03)}
.rank-num{flex-shrink:0;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:500}
.rank-num.r1{background:radial-gradient(circle at 35% 35%,#ffe55a,#c89000);color:#3d2800}
.rank-num.r2{background:radial-gradient(circle at 35% 35%,#e8e8e8,#888);color:#2a2a2a}
.rank-num.r3{background:radial-gradient(circle at 35% 35%,#e8a050,#804010);color:#2a1000}
.rank-num.rn{background:var(--faint);color:var(--muted)}
.rank-info{flex:1;min-width:0}
.rank-name{font-size:15px;font-weight:600;color:var(--cream);line-height:1.3;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rank-card.top1 .rank-name{color:var(--gold)}
.rank-card.top2 .rank-name{color:var(--silver)}
.rank-card.top3 .rank-name{color:var(--bronze)}
.rank-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.state-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500;padding:2px 6px;border-radius:3px;background:var(--faint);color:var(--muted);letter-spacing:.05em}
.contest-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;padding:2px 6px;border-radius:3px;letter-spacing:.04em}
.contest-tag.cbc      {background:rgba(245,194,48,.1);color:#c49a20}
.contest-tag.blumenau {background:rgba(91,163,208,.1);color:#5ba3d0}
.contest-tag.bbc      {background:rgba(76,175,120,.1);color:#4caf78}
.contest-tag.abracerva{background:rgba(180,100,220,.1);color:#b464dc}
.style-count-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted)}
.rank-medals{display:flex;align-items:center;gap:10px;flex-shrink:0;margin:0 8px}
.medal-col{display:flex;flex-direction:column;align-items:center;gap:2px}
.medal-icon{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.medal-icon.ouro  {background:radial-gradient(circle at 35% 35%,#ffe55a,#c89000);color:#3d2800}
.medal-icon.prata {background:radial-gradient(circle at 35% 35%,#e8e8e8,#888);color:#2a2a2a}
.medal-icon.bronze{background:radial-gradient(circle at 35% 35%,#e8a050,#804010);color:#2a1000}
.medal-count{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);line-height:1}
.medal-count.has{color:var(--cream)}
.rank-points{flex-shrink:0;text-align:right;min-width:60px}
.points-val{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:500;color:var(--amber);line-height:1}
.points-label{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase;margin-top:2px}
.medal-bar{display:flex;height:4px;border-radius:2px;overflow:hidden;margin-top:5px;gap:1px;max-width:200px}
.medal-bar-seg{border-radius:1px}
.medal-bar-seg.ouro  {background:var(--gold)}
.medal-bar-seg.prata {background:var(--silver)}
.medal-bar-seg.bronze{background:var(--bronze)}

/* ─── GOLD SPECIALISTS ────────────────────────────────────── */
.gold-ratio-wrap{margin-top:5px;display:flex;align-items:center;gap:8px}
.gold-ratio-bar{flex:1;max-width:160px;height:5px;background:var(--faint);border-radius:3px;overflow:hidden}
.gold-ratio-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,#c89000,#ffe55a)}
.gold-ratio-pct{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--gold);flex-shrink:0}
.n-medals-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted)}

/* ─── CONSISTENCY ─────────────────────────────────────────── */
.consistency-table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace}
.consistency-table th{padding:9px 14px;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500;text-align:left;border-bottom:1px solid var(--border)}
.consistency-table th.num{text-align:right}
.consistency-table td{padding:10px 14px;font-size:13px;border-bottom:1px solid var(--faint);vertical-align:middle}
.consistency-table tr:last-child td{border-bottom:none}
.consistency-table tr:hover td{background:var(--card-hover)}
.ct-rank{color:var(--muted);font-size:12px;width:36px}
.ct-name{color:var(--cream);font-weight:500}
.ct-state{color:var(--muted)}
.ct-pts{text-align:right;color:var(--muted)}
.ct-pts b{color:var(--cream)}
.ct-total{text-align:right;color:var(--amber);font-weight:500;font-size:15px}

/* ─── EVOLUTION ───────────────────────────────────────────── */
.evo-columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.evo-col-title{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.07em;text-transform:uppercase;font-weight:500;margin-bottom:10px}
.evo-col-title.gains{color:var(--green)}
.evo-col-title.losses{color:var(--red)}
.evo-list{display:flex;flex-direction:column;gap:5px}
.evo-card{display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--border);border-radius:7px;padding:10px 14px;transition:background .15s}
.evo-card:hover{background:var(--card-hover)}
.evo-card.gain {border-left:3px solid rgba(76,175,120,.5)}
.evo-card.loss {border-left:3px solid rgba(224,85,85,.5)}
.evo-info{flex:1;min-width:0}
.evo-name{font-size:13px;font-weight:600;color:var(--cream);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.evo-pts{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);margin-top:2px}
.evo-pts .prev{color:var(--muted)}
.evo-pts .arr{color:var(--faint);margin:0 4px}
.evo-pts .curr{color:var(--cream)}
.evo-delta{flex-shrink:0;font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:500;text-align:right;min-width:50px}
.evo-delta.pos{color:var(--green)}
.evo-delta.neg{color:var(--red)}

/* ─── DIVERSITY GRID ──────────────────────────────────────── */
.diversity-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.div-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;transition:background .15s}
.div-card:hover{background:var(--card-hover)}
.div-rank-name{display:flex;align-items:center;gap:8px}
.div-num{flex-shrink:0;width:24px;height:24px;border-radius:50%;background:var(--faint);color:var(--muted);display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500}
.div-name{font-size:13px;font-weight:600;color:var(--cream);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.div-stats{display:flex;align-items:center;gap:10px}
.div-styles-count{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--amber)}
.div-state{font-family:'IBM Plex Mono',monospace;font-size:10px;padding:2px 6px;border-radius:3px;background:var(--faint);color:var(--muted);letter-spacing:.05em}
.div-pts{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted)}

/* ─── STATE PILLS ─────────────────────────────────────────── */
.state-pills{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:16px}
.state-pill-btn{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;padding:4px 10px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;transition:all .15s;letter-spacing:.05em}
.state-pill-btn:hover:not(.empty){border-color:var(--amber-dim);color:var(--amber)}
.state-pill-btn.active{background:var(--amber);color:var(--bg);border-color:var(--amber)}
.state-pill-btn.empty{color:var(--faint);border-color:var(--faint);cursor:default;opacity:.5}

/* ─── GENERIC TABLE ───────────────────────────────────────── */
.data-table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace}
.data-table th{padding:9px 14px;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500;text-align:left;border-bottom:1px solid var(--border)}
.data-table th.num{text-align:right}
.data-table td{padding:10px 14px;font-size:12px;border-bottom:1px solid var(--faint);vertical-align:middle;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px}
.data-table td.wide{max-width:none;white-space:normal}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:hover td{background:var(--card-hover)}
.data-table .td-rank{color:var(--muted);font-size:11px;width:30px}
.data-table .td-style{color:var(--cream);font-size:12px}
.data-table .td-brewery{color:#c0a878;font-size:12px}
.data-table .td-state2{color:var(--muted);font-size:11px}
.data-table .td-pts{color:var(--amber);font-weight:500;text-align:right}
.data-table .td-gold{color:var(--gold)!important;text-align:right}
.data-table .td-silver{color:var(--silver)!important;text-align:right}
.data-table .td-bronze-col{color:var(--bronze)!important;text-align:right}
.data-table .td-unique{color:var(--cream);text-align:right}
.data-table .td-total{color:var(--muted);text-align:right}
.mini-badge{
  display:inline-flex;align-items:center;gap:3px;
  font-size:10px;padding:1px 5px;border-radius:3px;
  background:var(--faint);color:var(--muted);
}
.mini-badge.ou{background:rgba(255,215,0,.12);color:var(--gold)}
.mini-badge.pr{background:rgba(200,200,200,.1);color:var(--silver)}
.mini-badge.br{background:rgba(205,127,50,.12);color:var(--bronze)}

/* ─── CONTESTED BAR ───────────────────────────────────────── */
.contested-bar-wrap{display:flex;align-items:center;gap:8px}
.contested-bar{flex:1;height:6px;background:var(--faint);border-radius:3px;overflow:hidden;max-width:200px}
.contested-bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,#4a7fa0,#5ba3d0)}

/* ─── STATE DOMINANT STYLE ────────────────────────────────── */
.state-style-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:8px}
.ss-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:6px;transition:background .15s;min-height:80px}
.ss-card:hover{background:var(--card-hover)}
.ss-card.empty{opacity:.4;cursor:default}
.ss-state{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:500;color:var(--amber);letter-spacing:.06em}
.ss-style{font-size:12px;color:var(--cream);line-height:1.3;flex:1}
.ss-style.empty-label{color:var(--muted);font-style:italic;font-size:11px}
.ss-medals{display:flex;gap:5px;margin-top:2px}
.ss-medal-chip{font-family:'IBM Plex Mono',monospace;font-size:10px;padding:1px 5px;border-radius:3px}
.ss-medal-chip.ou{background:rgba(255,215,0,.12);color:var(--gold)}
.ss-medal-chip.pr{background:rgba(200,200,200,.1);color:var(--silver)}
.ss-medal-chip.br{background:rgba(205,127,50,.12);color:var(--bronze)}

/* ─── STYLES LEAST ────────────────────────────────────────── */
.styles-least-list{display:flex;flex-direction:column;gap:5px}
.style-least-card{display:flex;align-items:center;gap:14px;background:var(--card);border:1px solid var(--border);border-radius:7px;padding:11px 16px;transition:background .15s}
.style-least-card:hover{background:var(--card-hover)}
.sl-rank{flex-shrink:0;width:28px;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--muted);text-align:center}
.sl-name{flex:1;min-width:0;font-size:13px;font-weight:500;color:var(--cream);line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sl-medals{display:flex;align-items:center;gap:8px;flex-shrink:0}
.sl-medal-item{display:flex;align-items:center;gap:3px}
.sl-medal-icon{width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.sl-medal-icon.ouro  {background:radial-gradient(circle at 35% 35%,#ffe55a,#c89000);color:#3d2800}
.sl-medal-icon.prata {background:radial-gradient(circle at 35% 35%,#e8e8e8,#888);color:#2a2a2a}
.sl-medal-icon.bronze{background:radial-gradient(circle at 35% 35%,#e8a050,#804010);color:#2a1000}
.sl-medal-n{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted)}
.sl-medal-n.has{color:var(--cream)}
.sl-total{flex-shrink:0;min-width:52px;text-align:right;font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--muted)}
.sl-total b{color:var(--cream)}

/* ─── STATE TABLE ─────────────────────────────────────────── */
.state-table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace}
.state-table th{padding:9px 14px;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500;text-align:left;border-bottom:1px solid var(--border)}
.state-table th.num{text-align:right}
.state-table td{padding:11px 14px;font-size:13px;border-bottom:1px solid var(--faint);vertical-align:middle}
.state-table tr:last-child td{border-bottom:none}
.state-table tr:hover td{background:var(--card-hover)}
.state-table tr.st-empty td{color:var(--faint);font-style:italic}
.state-table tr:not(.st-empty){cursor:pointer}
.td-rank{color:var(--muted);font-size:12px;width:36px}
.td-state{color:var(--cream);font-weight:500;font-size:13px;letter-spacing:.06em}
.td-pts{color:var(--amber);font-weight:500;font-size:15px;text-align:right}
.td-medal{text-align:right;color:var(--muted)}
.td-medal b{color:var(--cream)}
.td-brew{text-align:right;color:var(--muted);font-size:11px}
.td-gold  {color:var(--gold)!important}
.td-silver{color:var(--silver)!important}
.td-bronze-col{color:var(--bronze)!important}
.state-row-bar{display:flex;height:3px;border-radius:2px;overflow:hidden;gap:1px;margin-top:4px}

/* ─── RANK DETAIL ─────────────────────────────────────────── */
.rank-card{cursor:pointer}
.rank-detail{background:var(--faint);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:14px 16px;margin-top:-6px;margin-bottom:6px}
.detail-group{margin-bottom:12px}
.detail-group:last-child{margin-bottom:0}
.detail-group-title{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.detail-year-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.04em}
.detail-entries{display:flex;flex-direction:column;gap:4px}
.detail-entry{display:flex;align-items:center;gap:8px;padding:4px 0}
.detail-medal-icon{width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;font-family:'IBM Plex Mono',monospace;flex-shrink:0}
.detail-medal-icon.ouro  {background:radial-gradient(circle at 35% 35%,#ffe55a,#c89000);color:#3d2800}
.detail-medal-icon.prata {background:radial-gradient(circle at 35% 35%,#e8e8e8,#888);color:#2a2a2a}
.detail-medal-icon.bronze{background:radial-gradient(circle at 35% 35%,#e8a050,#804010);color:#2a1000}
.detail-beer{font-size:12px;color:var(--cream);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.detail-style-tag{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);flex-shrink:0;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ─── EMPTY STATE ─────────────────────────────────────────── */
.empty-state{padding:40px;text-align:center;color:var(--muted);font-size:13px;font-style:italic}

::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--faint);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--amber-dim)}

/* ─── MOBILE ─────────────────────────────────────────────── */
@media(max-width:900px){.evo-columns{grid-template-columns:1fr}}
@media(max-width:768px){
  :root{--header-h:54px}
  .header-subtitle,.scoring-legend{display:none}
  .rank-medals{gap:6px;margin:0 4px}
  .medal-bar,.gold-ratio-wrap{display:none}
  .rank-card{padding:11px 12px;gap:10px}
  .diversity-grid{grid-template-columns:1fr 1fr}
  .state-style-grid{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
  .sl-medals{display:none}
}
@media(max-width:480px){
  .header-logo-img{height:24px}
  .year-btn,.nav-link{font-size:10px;padding:2px 7px}
  .diversity-grid,.state-style-grid{grid-template-columns:1fr 1fr}
  .rank-medals{display:none}
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
    <a href="index.html" class="nav-link active">Ranking</a>
    <a href="medals.html" class="nav-link">Medalhas</a>
  </nav>
  <div class="year-filter">
    <button class="year-btn" data-year="all">Todos</button>
    ''' + ''.join(f'<button class="year-btn" data-year="{y}">{y}</button>' for y in DATA['years']) + '''
  </div>
  <div class="header-right">
    <div class="scoring-legend">
      <span class="s-ouro">Ouro = 3 pts</span>
      <span>·</span>
      <span class="s-prata">Prata = 2 pts</span>
      <span>·</span>
      <span class="s-bronze">Bronze = 1 pt</span>
    </div>
  </div>
</header>

<main class="ranking-main">

  <!-- 1. Top 10 Cervejarias -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Top 10 Cervejarias</h2>
      <span class="section-desc" id="overall-desc"></span>
      <span class="section-count" id="overall-count"></span>
    </div>
    <div class="concentration-stats" id="concentration-stats"></div>
    <div class="rank-list" id="top10-list"></div>
  </section>

  <!-- 3. Consistência entre Anos (all-year only) -->
  <section class="ranking-section section-only-all" id="section-consistency">
    <div class="section-header">
      <h2 class="section-title">Consistência entre Anos</h2>
      <span class="section-desc">cervejarias premiadas em todos os anos disponíveis</span>
      <span class="section-count" id="consistency-count"></span>
    </div>
    <table class="consistency-table">
      <thead id="consistency-thead"></thead>
      <tbody id="consistency-body"></tbody>
    </table>
  </section>

  <!-- 4. Maior Evolução (all-year only) -->
  <section class="ranking-section section-only-all" id="section-evolution">
    <div class="section-header">
      <h2 class="section-title">Maior Evolução</h2>
      <span class="section-desc" id="evo-desc"></span>
    </div>
    <div class="evo-columns">
      <div>
        <div class="evo-col-title gains">Maiores Ganhos</div>
        <div class="evo-list" id="evo-gains"></div>
      </div>
      <div>
        <div class="evo-col-title losses">Maiores Quedas</div>
        <div class="evo-list" id="evo-losses"></div>
      </div>
    </div>
  </section>

  <!-- 5. Diversidade de Estilos -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Diversidade de Estilos</h2>
      <span class="section-desc">cervejarias com mais categorias de estilo distintas vencidas</span>
    </div>
    <div class="diversity-grid" id="diversity-grid"></div>
  </section>

  <!-- 6. Top 10 por Estado -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Top 10 por Estado</h2>
      <span class="section-count" id="state-section-count"></span>
    </div>
    <div class="state-pills" id="state-pills"></div>
    <div class="rank-list" id="top10-state-list"></div>
  </section>

  <!-- 7. Ranking de Estados -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Ranking de Estados</h2>
      <span class="section-desc">pontuação agregada de todas as cervejarias por UF</span>
    </div>
    <table class="state-table">
      <thead>
        <tr>
          <th>#</th><th>Estado</th><th class="num">Cervejarias</th>
          <th class="num">Ouro</th><th class="num">Prata</th><th class="num">Bronze</th>
          <th class="num">Pontos</th>
        </tr>
      </thead>
      <tbody id="state-ranking-body"></tbody>
    </table>
  </section>

  <!-- 8. Estilo Dominante por Estado -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Estilo Dominante por Estado</h2>
      <span class="section-desc">categoria com mais medalhas por UF</span>
    </div>
    <div class="state-style-grid" id="state-style-grid"></div>
  </section>

  <!-- 9. Dominância por Estilo -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Dominância por Estilo</h2>
      <span class="section-desc">cervejaria com mais pontos em cada categoria · top 25</span>
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>#</th><th>Estilo</th><th>Cervejaria</th><th>UF</th>
          <th class="num">Ouro</th><th class="num">Prata</th><th class="num">Bronze</th>
          <th class="num">Pts</th>
        </tr>
      </thead>
      <tbody id="style-dominance-body"></tbody>
    </table>
  </section>

  <!-- 11. Estilos Menos Premiados -->
  <section class="ranking-section">
    <div class="section-header">
      <h2 class="section-title">Estilos Menos Premiados</h2>
      <span class="section-desc">categorias com menos medalhas distribuídas · oportunidades de menor concorrência</span>
    </div>
    <div class="styles-least-list" id="styles-least-list"></div>
  </section>

</main>

<script>
const RANKING_BY_YEAR = ''' + RKJ + ''';
const CROSS_YEAR      = ''' + CYJ + ''';
const YEARS           = ''' + YEARS_J + ''';
const ALL_STATES      = ''' + STATES_J + ''';

let currentYear  = 'all';
let currentState = null;

function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function getRank(){ return RANKING_BY_YEAR[currentYear]; }

function rankNumHtml(n){
  const cls = n===1?'r1':n===2?'r2':n===3?'r3':'rn';
  return `<div class="rank-num ${cls}">${n}</div>`;
}
function medalColsHtml(b){
  return ['ouro','prata','bronze'].map(m=>{
    const n=b[m]||0;
    return `<div class="medal-col"><div class="medal-icon ${m}">${m[0].toUpperCase()}</div><span class="medal-count${n?' has':''}">${n||'—'}</span></div>`;
  }).join('');
}
function medalBarHtml(b,maxPts){
  if(!maxPts) return '';
  const ou=Math.round((b.ouro||0)*3/maxPts*100);
  const pr=Math.round((b.prata||0)*2/maxPts*100);
  const br=Math.round((b.bronze||0)/maxPts*100);
  let s='';
  if(ou) s+=`<div class="medal-bar-seg ouro" style="flex:${ou}"></div>`;
  if(pr) s+=`<div class="medal-bar-seg prata" style="flex:${pr}"></div>`;
  if(br) s+=`<div class="medal-bar-seg bronze" style="flex:${br}"></div>`;
  return s?`<div class="medal-bar">${s}</div>`:'';
}
function contestTagsHtml(contests){
  const map={cbc:'CBC',blumenau:'BLU',bbc:'BBC',abracerva:'CCB'};
  return (contests||[]).map(c=>`<span class="contest-tag ${c}">${map[c]||c}</span>`).join('');
}
function rankCardHtml(b,rank,maxPts,extraMeta=''){
  const topCls=rank===1?' top1':rank===2?' top2':rank===3?' top3':'';
  const detailId='detail-'+Math.random().toString(36).slice(2);
  const me=b.medal_entries||{};
  const CONTEST_NAMES={cbc:'CBC',blumenau:'Blumenau',bbc:'Brasil Beer Cup',abracerva:'Copa Cerveja Brasil'};
  const MEDAL_ORDER=['Ouro','Prata','Bronze'];
  let detailHtml='';
  for(const c of ['cbc','blumenau','bbc','abracerva']){
    if(!me[c]) continue;
    for(const y of Object.keys(me[c]).sort()){
      const entries=me[c][y];
      if(!entries||!entries.length) continue;
      const sorted=[...entries].sort((a,b)=>MEDAL_ORDER.indexOf(a.medal)-MEDAL_ORDER.indexOf(b.medal));
      detailHtml+=`<div class="detail-group"><div class="detail-group-title"><span class="contest-tag ${c}">${CONTEST_NAMES[c]||c}</span><span class="detail-year-tag">${y}</span></div><div class="detail-entries">${sorted.map(en=>`<div class="detail-entry ${en.medal.toLowerCase()}"><div class="detail-medal-icon ${en.medal.toLowerCase()}">${en.medal[0]}</div><span class="detail-beer">${esc(en.beer)}</span><span class="detail-style-tag">${esc(en.style)}</span></div>`).join('')}</div></div>`;
    }
  }
  return `<div class="rank-card${topCls}" onclick="toggleDetail('${detailId}')">
    ${rankNumHtml(rank)}
    <div class="rank-info">
      <div class="rank-name" title="${esc(b.display)}">${esc(b.display)}</div>
      <div class="rank-meta">
        <span class="state-tag">${esc(b.state||'?')}</span>
        ${contestTagsHtml(b.contests)}
        <span class="style-count-tag">${b.n_styles} estilo${b.n_styles!==1?'s':''}</span>
        ${extraMeta}
      </div>
      ${medalBarHtml(b,maxPts)}
    </div>
    <div class="rank-medals">${medalColsHtml(b)}</div>
    <div class="rank-points"><div class="points-val">${b.points}</div><div class="points-label">pontos</div></div>
  </div>
  <div class="rank-detail" id="${detailId}" style="display:none">${detailHtml||'<div class="empty-state">Sem detalhes disponíveis.</div>'}</div>`;
}
function toggleDetail(id){
  const el=document.getElementById(id);
  if(el) el.style.display=el.style.display==='none'?'block':'none';
}

// ── 1. Top 10 Overall ────────────────────────────────────────
function renderTop10Overall(){
  const rk=getRank(), list=rk.top10_overall||[], maxPts=list.length?list[0].points:1;
  const cNames={cbc:'CBC',blumenau:'Blumenau',bbc:'BBC',abracerva:'Copa Cerveja Brasil'};
  const activeStr=currentYear==='all'
    ? YEARS.join(' + ')+' — todos os anos'
    : (rk.active_contests||[]).map(c=>cNames[c]||c).join(' + ');
  document.getElementById('overall-desc').textContent=activeStr;
  document.getElementById('overall-count').textContent=`${rk.total_breweries} cervejarias`;

  // Concentration
  const mc=rk.medal_concentration||{};
  document.getElementById('concentration-stats').innerHTML=
    `<span class="conc-item">Top 10 concentram <b>${mc.pts_pct||0}%</b> dos pontos</span>
     <div class="conc-bar-wrap"><div class="conc-bar-fill" style="width:${mc.pts_pct||0}%"></div></div>
     <span class="conc-item"><b>${mc.medal_pct||0}%</b> das medalhas</span>
     <span style="margin-left:auto;color:var(--faint)">|</span>
     <span class="conc-item">${mc.total_medals||0} medalhas · ${mc.total_pts||0} pts totais</span>`;

  document.getElementById('top10-list').innerHTML=list.length
    ?list.map((b,i)=>rankCardHtml(b,i+1,maxPts)).join('')
    :'<div class="empty-state">Sem dados.</div>';
}


// ── 3. Consistency ───────────────────────────────────────────
function renderConsistency(){
  const cy=CROSS_YEAR, list=cy.consistency||[], yrs=cy.years||[];
  document.getElementById('consistency-count').textContent=`${list.length} cervejaria${list!==1?'s':''}`;
  document.getElementById('consistency-thead').innerHTML=
    `<tr><th>#</th><th>Cervejaria</th><th>UF</th>
     ${yrs.map(y=>`<th class="num">${y}</th>`).join('')}
     <th class="num">Total</th></tr>`;
  document.getElementById('consistency-body').innerHTML=list.length
    ?list.map((b,i)=>`<tr>
        <td class="ct-rank">${i+1}</td>
        <td class="ct-name">${esc(b.display)}</td>
        <td class="ct-state">${esc(b.state||'?')}</td>
        ${yrs.map(y=>`<td class="ct-pts"><b>${b.pts_by_year[y]||0}</b></td>`).join('')}
        <td class="ct-total">${b.total_pts}</td>
      </tr>`).join('')
    :'<tr><td colspan="99" style="padding:20px;text-align:center;color:var(--muted);font-style:italic">Sem cervejarias em todos os anos.</td></tr>';
}

// ── 4. Evolution ─────────────────────────────────────────────
function renderEvolution(){
  const ev=CROSS_YEAR.evolution||{};
  const py=ev.prev_year, cy2=ev.curr_year;
  document.getElementById('evo-desc').textContent=
    py&&cy2?`variação de pontos entre ${py} e ${cy2}`:'';

  function evoCardHtml(e,type){
    const pos=e.delta>=0;
    const sign=pos?'+':'';
    return `<div class="evo-card ${type}">
      <div class="evo-info">
        <div class="evo-name" title="${esc(e.display)}">${esc(e.display)}</div>
        <div class="evo-pts">
          <span class="prev">${e.prev_pts}</span>
          <span class="arr">→</span>
          <span class="curr">${e.curr_pts}</span>
          <span class="state-tag" style="margin-left:4px">${esc(e.state||'?')}</span>
        </div>
      </div>
      <div class="evo-delta ${pos?'pos':'neg'}">${sign}${e.delta}</div>
    </div>`;
  }
  document.getElementById('evo-gains').innerHTML=(ev.gains||[]).map(e=>evoCardHtml(e,'gain')).join('')||'<div class="empty-state">Sem dados.</div>';
  document.getElementById('evo-losses').innerHTML=(ev.losses||[]).map(e=>evoCardHtml(e,'loss')).join('')||'<div class="empty-state">Sem dados.</div>';
}

// ── 5. Diversity ─────────────────────────────────────────────
function renderDiversity(){
  const list=getRank().diversity_top10||[];
  document.getElementById('diversity-grid').innerHTML=list.length
    ?list.map((b,i)=>`<div class="div-card">
        <div class="div-rank-name"><div class="div-num">${i+1}</div>
        <span class="div-name" title="${esc(b.display)}">${esc(b.display)}</span></div>
        <div class="div-stats">
          <span class="div-styles-count">${b.n_styles} estilo${b.n_styles!==1?'s':''}</span>
          <span class="div-state">${esc(b.state||'?')}</span>
          <span class="div-pts">${b.points} pts</span>
        </div>
      </div>`).join('')
    :'<div class="empty-state">Sem dados.</div>';
}

// ── 6. Top 10 by State ───────────────────────────────────────
function renderStatePills(){
  const rk=getRank(), withData=new Set(rk.states_with_data||[]);
  document.getElementById('state-pills').innerHTML=ALL_STATES.map(st=>{
    const has=withData.has(st), isActive=currentState===st;
    return `<button class="state-pill-btn${isActive?' active':''}${!has?' empty':''}"
      data-state="${esc(st)}"${!has?' disabled':''}>${esc(st)}</button>`;
  }).join('');
  document.querySelectorAll('.state-pill-btn:not(.empty)').forEach(btn=>{
    btn.addEventListener('click',()=>{currentState=btn.dataset.state;renderStatePills();renderTop10State();});
  });
}
function renderTop10State(){
  const rk=getRank(), countEl=document.getElementById('state-section-count'),
        container=document.getElementById('top10-state-list');
  if(!currentState){
    countEl.textContent='';
    container.innerHTML='<div class="empty-state">Selecione um estado acima.</div>';return;
  }
  const list=(rk.top10_by_state||{})[currentState]||[], maxPts=list.length?list[0].points:1;
  countEl.textContent=currentState;
  container.innerHTML=list.length
    ?list.map((b,i)=>rankCardHtml(b,i+1,maxPts)).join('')
    :`<div class="empty-state">Nenhuma cervejaria de ${esc(currentState)} com medalhas neste período.</div>`;
}

// ── 7. State ranking table ───────────────────────────────────
function renderStateRanking(){
  const totals=getRank().state_totals||[];
  const maxPts=(totals.find(s=>s.points>0)||{points:1}).points;
  let rank=0;
  document.getElementById('state-ranking-body').innerHTML=totals.map(s=>{
    const empty=s.breweries===0;
    if(!empty) rank++;
    const ou=empty?0:Math.round(s.ouro*3/maxPts*100);
    const pr=empty?0:Math.round(s.prata*2/maxPts*100);
    const br=empty?0:Math.round(s.bronze/maxPts*100);
    const bar=(ou||pr||br)?`<div class="state-row-bar">
      ${ou?`<div class="medal-bar-seg ouro" style="flex:${ou}"></div>`:''}
      ${pr?`<div class="medal-bar-seg prata" style="flex:${pr}"></div>`:''}
      ${br?`<div class="medal-bar-seg bronze" style="flex:${br}"></div>`:''}
    </div>`:'';
    return `<tr${empty?' class="st-empty"':` onclick="selectState('${s.state}')" style="cursor:pointer"`}>
      <td class="td-rank">${empty?'—':rank}</td>
      <td class="td-state">${esc(s.state)}</td>
      <td class="td-brew" style="text-align:right">${empty?'—':s.breweries}</td>
      <td class="td-medal td-gold"   style="text-align:right">${empty?'—':`<b>${s.ouro}</b>`}</td>
      <td class="td-medal td-silver" style="text-align:right">${empty?'—':`<b>${s.prata}</b>`}</td>
      <td class="td-medal td-bronze-col" style="text-align:right">${empty?'—':`<b>${s.bronze}</b>`}</td>
      <td class="td-pts">${empty?'—':s.points+bar}</td>
    </tr>`;
  }).join('');
}

function selectState(st){
  currentState=st;
  renderStatePills();
  renderTop10State();
  document.getElementById('state-section-count').closest('section').scrollIntoView({behavior:'smooth'});
}

// ── 8. State dominant style ──────────────────────────────────
function renderStateDominantStyle(){
  const map=getRank().state_dominant_style||{};
  document.getElementById('state-style-grid').innerHTML=ALL_STATES.map(st=>{
    const d=map[st];
    if(!d) return `<div class="ss-card empty"><div class="ss-state">${esc(st)}</div><div class="ss-style empty-label">sem dados</div></div>`;
    return `<div class="ss-card">
      <div class="ss-state">${esc(st)}</div>
      <div class="ss-style">${esc(d.style)}</div>
      <div class="ss-medals">
        ${d.ouro  ?`<span class="ss-medal-chip ou">${d.ouro}O</span>`:''}
        ${d.prata ?`<span class="ss-medal-chip pr">${d.prata}P</span>`:''}
        ${d.bronze?`<span class="ss-medal-chip br">${d.bronze}B</span>`:''}
      </div>
    </div>`;
  }).join('');
}

// ── 9. Style dominance table ─────────────────────────────────
function renderStyleDominance(){
  const list=getRank().style_dominance||[];
  document.getElementById('style-dominance-body').innerHTML=list.length
    ?list.map((s,i)=>`<tr>
        <td class="td-rank">${i+1}</td>
        <td class="td-style">${esc(s.style)}</td>
        <td class="td-brewery">${esc(s.brewery)}</td>
        <td class="td-state2">${esc(s.state||'?')}</td>
        <td class="td-gold">${s.ouro||'—'}</td>
        <td class="td-silver">${s.prata||'—'}</td>
        <td class="td-bronze-col">${s.bronze||'—'}</td>
        <td class="td-pts">${s.points}</td>
      </tr>`).join('')
    :'<tr><td colspan="8" class="empty-state">Sem dados.</td></tr>';
}

// ── 11. Styles least medals ──────────────────────────────────
function renderStylesLeast(){
  const list=getRank().styles_least_medals||[];
  document.getElementById('styles-least-list').innerHTML=list.length
    ?list.map((s,i)=>{
        const medals=['ouro','prata','bronze'].map(m=>{
          const n=s[m]||0;
          return `<div class="sl-medal-item"><div class="sl-medal-icon ${m}">${m[0].toUpperCase()}</div><span class="sl-medal-n${n?' has':''}">${n||'—'}</span></div>`;
        }).join('');
        return `<div class="style-least-card">
          <div class="sl-rank">${i+1}</div>
          <div class="sl-name" title="${esc(s.style)}">${esc(s.style)}</div>
          <div class="sl-medals">${medals}</div>
          <div class="sl-total"><b>${s.total}</b> medalha${s.total!==1?'s':''}</div>
        </div>`;
      }).join('')
    :'<div class="empty-state">Sem dados.</div>';
}

// ── Year toggle & all-only visibility ────────────────────────
function setAllOnlyVisibility(){
  const isAll=currentYear==='all';
  document.querySelectorAll('.section-only-all').forEach(el=>{
    el.style.display=isAll?'':'none';
  });
}

document.querySelectorAll('.year-btn').forEach(btn=>{
  if(btn.dataset.year===currentYear) btn.classList.add('active');
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.year-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    currentYear=btn.dataset.year;
    currentState=null;
    renderAll();
  });
});

function renderAll(){
  setAllOnlyVisibility();
  renderTop10Overall();
  if(currentYear==='all'){renderConsistency();renderEvolution();}
  renderDiversity();
  renderStatePills();
  renderTop10State();
  renderStateRanking();
  renderStateDominantStyle();
  renderStyleDominance();
  renderStylesLeast();
}

renderAll();
</script>
</body>
</html>
'''

out = BASE / 'index.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(HTML)

# Stats
for key in list(DATA['years']) + ['all']:
    rk   = RANKING_BY_YEAR[key]
    top  = rk['top10_overall']
    lbl  = 'ALL YEARS' if key == 'all' else key
    print(f'\n{lbl}')
    top3 = ' | '.join(f'#{b["rank"]} {b["display"]} {b["points"]}pts' for b in top[:3])
    print(f'  Top 3: {top3}')
    print(f'  Gold specialist #1: {rk["gold_specialists"][0]["display"] if rk["gold_specialists"] else "—"} ({rk["gold_specialists"][0].get("gold_ratio",0)}% ouro)' if rk['gold_specialists'] else '  No gold specialists')
    mc = rk['medal_concentration']
    print(f'  Concentration: top10 = {mc["pts_pct"]}% pts, {mc["medal_pct"]}% medals')
    print(f'  Most contested style: {rk["styles_most_contested"][0]["style"]} ({rk["styles_most_contested"][0]["unique_breweries"]} cervejarias)' if rk['styles_most_contested'] else '')

cy = CROSS_YEAR
print(f'\nConsistência: {len(cy["consistency"])} cervejarias em todos os anos')
ev = cy['evolution']
if ev['gains']:
    print(f'Maior ganho: {ev["gains"][0]["display"]} +{ev["gains"][0]["delta"]} pts ({ev["prev_year"]}→{ev["curr_year"]})')
if ev['losses']:
    print(f'Maior queda: {ev["losses"][0]["display"]} {ev["losses"][0]["delta"]} pts ({ev["prev_year"]}→{ev["curr_year"]})')
print(f'\nindex.html written ({out.stat().st_size // 1024}KB)')
