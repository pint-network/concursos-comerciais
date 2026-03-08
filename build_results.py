#!/usr/bin/env python3
"""
Build results.json from all CSV files (CBC 2025/2026 + Blumenau 2025/2026).

- Normalises style names for CBC 2025 (truncated/malformed due to PDF layout)
- Normalises brewery names so the same brewery is recognised across contests
- Produces a canonical display name for each brewery (prefer "Cervejaria X" form)
- Writes results.json consumed by build_dashboard.py
"""
import csv, json, re
from collections import defaultdict
from pathlib import Path

BASE = Path('/Users/hboavent/Projects/personal/concursos-resultados')

# ── Canonical style lookup (from Blumenau 2025 + CBC 2026 + Blumenau 2026) ──────────────
def _load_canonical_styles():
    styles = set()
    for fname in ('concurso-brasileiro-de-cervejas-2025-results.csv',
                  'cbc-2026-results.csv',
                  'concurso-brasileiro-de-cervejas-results.csv'):
        for r in csv.DictReader(open(BASE / fname, encoding='utf-8')):
            styles.add(r['style'].strip())
    return styles


# ── BBC 2025 style fixes ─────────────────────────────────────────────────────
# Maps BBC 2025 style names to canonical forms used in other contests.
BBC_STYLE_MAP = {
    # BBC uses Portuguese category names for Brazilian styles
    'Brazilian Beer -Catharina Sour':                              'Catharina Sour',
    'Brazilian Beer Com Ervas E Especiarias':                      'Brazilian Herb and Spiced Beer',
    'Brazilian Beer Com Frutas':                                   'Brazilian Fruit Beer',
    'Brazilian Beer Com Madeira':                                  'Brazilian Wood Aged Beer',
    # Wood/barrel: BBC omits space before "and"
    'Wood-And Barrel-Aged Beer':                                   'Wood- and Barrel-Aged Beer',
    'Wood-And Barrel-Aged Sour Beer':                              'Wood- and Barrel-Aged Sour Beer',
    # Bohemian = Czech
    'Bohemian-Style Pilsener':                                     'Czech-Style Pale Lager',
}

CANONICAL_STYLES = _load_canonical_styles()

# ── Manual style fixes: (style_raw, beer_lower, brewery_lower) -> canonical ─────────────
# Used for ambiguous truncated styles in CBC 2025
STYLE_FIXES_MANUAL = {
    # American-Style (ambiguous)
    ('American-Style', 'in "trigo" we',    'cervejaria karsten'):   'American-Style Wheat Beer',
    ('American-Style', 'premium lager',    'cervejaria salva'):      'American-Style Lager',
    ('American-Style', 'imperial black',   'cervejaria big jack'):   'American-Style Black Ale',
    # American-Style Imperial
    ('American-Style Imperial', 'maestro noturno', 'cervejaria maestro'): 'American-Style Imperial Stout',
    ('American-Style Imperial', 'tormenta',         'cervejaria marés'):   'American-Style Imperial Stout',
    # American-Style India / India Pale
    ('American-Style India',      'ipa',      'cervejaria leopoldina'): 'American-Style India Pale Ale',
    ('American-Style India Pale', 'cold ipa', 'cervejaria stier'):      'American-Style India Pale Ale',
    # Australasian
    ('Australasian, Latin American', 'premium lager -', 'cervejaria urwald'):
        'Australasian, Latin American or Tropical-Style Light Lager',
    # Bamberg-Style
    ('Bamberg-Style', 'märzen rauchbier', 'cervejaria bierbaum'): 'Bamberg-Style Maerzen Rauchbier',
    # Belgian-Style
    ('Belgian-Style', 'session ale', 'cervejaria opa bier'): 'Belgian-Style Session Ale',
    ('Belgian-Style Strong', 'freyr', 'cervejaria traum'):    'Belgian-Style Strong Blonde Ale',
    # Contemporary American-Style
    ('Contemporary American-Style', 'hop lager',   'cervejaria 277 craft beer'): 'Contemporary American-Style Lager',
    ('Contemporary American-Style', 'pilsen',      'cervejaria fredericia'):      'Contemporary American-Style Pilsener',
    ('Contemporary American-Style', 'light lager', 'cervejaria mina beer'):       'Contemporary American-Style Light Lager',
    # German-Style
    ('German-Style', 'me enganaram', 'cervejaria karsten'):  'German-Style Koelsch',
    ('German-Style', 'doppelbock',   'cervejaria bierbaum'): 'German-Style Doppelbock',
    # International-Style
    ('International-Style', 'morango joinville bier álcool', 'cervejaria opa bier'): 'International-Style Pilsener',
    # New Zealand-Style
    ('New Zealand-Style', 'new zealand', 'cervejaria big jack'): 'New Zealand-Style Pale Ale',
    # South German-Style
    ('South German-Style', 'weiss',        'cervejaria stier'):         'South German-Style Hefeweizen',
    ('South German-Style', 'amber weiss',  'cervejaria dona lupulina'): 'South German-Style Bernsteinfarbenes Weizen',
    ('South German-Style', 'weizenbock',   'cervejaria dama bier'):     'South German-Style Weizenbock',
    # West Coast
    ('West Coast-Style', 'west coast', 'cervejaria unika'): 'West Coast-Style India Pale Ale',
}

# Additional simple fixes for remaining UNKNOWN styles
STYLE_FIXES_SIMPLE = {
    'Ale Non-Alcohol Malt':                       'Non-Alcohol Malt Beverage',
    'American or Bamberg-Style Bock Lager':       'Traditional German-Style Bock',
    'American-Style Safra':                        'American-Style Lager',   # safra = harvest lager
    'Australasian, Latin Tropical-Style Light':    'Australasian, Latin American or Tropical-Style Light Lager',
    'Bamberg-Style Weiss':                         'South German-Style Hefeweizen',
    'Belgian-Style Flanders Bruin or Oud Red':    'Belgian-Style Flanders Oud Bruin or Oud Red Ale',
    'Bernsteinfarbenes Weizen Historical Beer':    'South German-Style Bernsteinfarbenes Weizen',
    'Beverage South German-Style Weizenbock':      'South German-Style Weizenbock',
    'Blonde Ale Specialty Honey Beer':             'Specialty Honey Beer',
    'Bock/ German-Style Wiesn':                   'Traditional German-Style Bock',
    'Bohemian-Style Pilsener':                     'Czech-Style Pale Lager',
    'Brazilian Fruit Beer':                        'Brazilian Fruit Beer',    # keep as-is (valid)
    'Brazilian Herb and':                          'Brazilian Herb and Spiced Beer',
    'Brazilian Herb and Spiced':                   'Brazilian Herb and Spiced Beer',
    'Brazilian Wood':                              'Brazilian Wood Aged Beer',
    'Brazilian Wood Aged Beer':                    'Brazilian Wood Aged Beer',  # already fine
    'Contemporary Style Pilsener':                 'Contemporary American-Style Pilsener',
    'Cream Ale American-Style Pale':               'American-Style Cream Ale',
    'Dark Lager Scottish-Style Light':             'American-Style Dark Lager',
    'Doppelbock Munich-Style':                     'German-Style Doppelbock',
    'Double Hoppy Red Wood':                       'Double Hoppy Red Ale',
    'Double India Pale Ale Pumpkin/Squash Beer':   'American-Style Imperial or Double India Pale Ale',
    'French-Style Bière de Garde':                 'Classic French & Belgian-Style Saison',
    'Fruit Beer Belgian-Style Blonde Ale':         'Belgian-Style Fruit Beer',
    'German-Style Heller Maibock Beer':            'German-Style Heller Bock/Maibock',
    'German-Style Oktoberfest/Wiesn':              'German-Style Oktoberfest/Festbier',
    'Gose Experimental India':                     'Experimental India Pale Ale',
    'Heavy Extra Special Bitter':                  'Extra Special Bitter',
    'India Belgian-Style':                         'Belgian-Style Tripel',
    'India Pale Ale Catharina Sour':               'Catharina Sour',
    'Italian Pilsener':                            'International-Style Pilsener',
    'Kentucky Common Weisse':                      'Berliner-Style Weisse',
    'Liquor German-Style Leichtbier':              'German-Style Leichtbier',
    'Maerzen Rauchbier German-Style':              'Bamberg-Style Maerzen Rauchbier',
    'Oktoberfest/Wiesn American-Style Dark':       'American-Style Dark Lager',
    'Oud Belgian-Style Strong Ale':                'Belgian-Style Strong Dark Ale',
    'Pale Ale American-Style Strong Pale Ale':     'American-Style Strong Pale Ale',
    'Pale Ale Belgian-Style Blonde Ale':           'Belgian-Style Blonde Ale',
    'Pale Ale Italian Grape Ale':                  'Italian Grape Ale',
    'Pale Ale Session Beer':                       'Session Beer',
    'Pilsener Berliner-Style Weisse':              'Berliner-Style Weisse',
    'Pilsener Bohemian-Style':                     'Czech-Style Pale Lager',
    'Pilsener Gluten-Free Beer':                   'Gluten-Free Beer',
    'Rauchbier Brazilian Fruit Beer':              'Brazilian Fruit Beer',
    'Rauchbier International-Style Pale Ale':      'International-Style Pale Ale',
    'Rauchbier South German-Style':                'South German-Style Hefeweizen',
    'Scottish-Style Heavy Storm':                  'Scottish Heavy Ale',
    'Sour Italian Grape Ale':                      'Italian Grape Ale',
    'South German-Style Dunkel':                   'South German-Style Hefeweizen',
    'Stout Wood- and Barrel-Aged Beer':            'Wood- and Barrel-Aged Beer',
    'Weizen Australian-Style Pale Ale':            'Australian-Style Pale Ale',
    'Weizenbock Wood- and Barrel-Aged':            'Wood- and Barrel-Aged Beer',
    'Wheat Wine Ale Specialty Honey Beer':         'Specialty Honey Beer',
    'Wine Ale American-Style Stout':               'American-Style Stout',
    'Wine Ale Dortmunder/European-Style Export Pau': 'Dortmunder/European-Style Export',
    'Wine Ale Juicy or Hazy Pale Ale':             'Juicy or Hazy Pale Ale',
    'Wine Ale Other Belgian-Style Ale':            'Other Belgian-Style Ale',
}


def fix_style_cbc2025(style_raw: str, beer: str, brewery: str) -> str:
    """Normalise a CBC 2025 style name to a canonical style."""
    # 1. Already canonical
    if style_raw in CANONICAL_STYLES:
        return style_raw

    # 2. Manual per-entry fix
    key = (style_raw, beer.lower(), brewery.lower())
    if key in STYLE_FIXES_MANUAL:
        return STYLE_FIXES_MANUAL[key]

    # 3. Simple lookup
    if style_raw in STYLE_FIXES_SIMPLE:
        return STYLE_FIXES_SIMPLE[style_raw]

    # 4. Strip leading "Ale ", "Beer ", "Lager " noise words
    for noise in ('Ale ', 'Beer ', 'Lager '):
        if style_raw.startswith(noise):
            candidate = style_raw[len(noise):]
            if candidate in CANONICAL_STYLES:
                return candidate

    # 5. Single prefix match (truncated style)
    candidates = [c for c in CANONICAL_STYLES if c.startswith(style_raw + ' ')]
    if len(candidates) == 1:
        return candidates[0]

    # 6. Suffix garbage (style has known canonical as prefix)
    for c in CANONICAL_STYLES:
        if style_raw.startswith(c + ' '):
            return c

    return style_raw   # give up, keep as-is


# ── Brewery name canonicalisation ────────────────────────────────────────────────────────

_STRIP_RE = re.compile(
    r'^(Cervejaria|Cerveja|Cervejas|Cia\.?)\s+|'
    r'\s+(Cervejaria|Cerveja|Cervejas|Brewing|Brewery|Brewpub|Bier|Beer)\s*$',
    re.IGNORECASE,
)

def brewery_key(name: str) -> str:
    """Return a normalised key for fuzzy brewery matching."""
    k = _STRIP_RE.sub('', name.strip())
    # also strip common suffixes like "Craft Beer", "Craft Brewery"
    k = re.sub(r'\s+(Craft Beer|Craft Brewery|Artesanal)\s*$', '', k, flags=re.IGNORECASE)
    return k.strip().lower()


def canonical_brewery_name(name_a: str | None, name_b: str | None) -> str:
    """Given names from contest A and B for the same brewery, pick the canonical display form.
    Prefer the one that has the 'Cervejaria' prefix, else the longer name."""
    names = [n for n in (name_a, name_b) if n]
    if not names:
        return ''
    if len(names) == 1:
        return names[0]
    # Prefer name that starts with "Cervejaria"
    for n in names:
        if re.match(r'^Cervejaria\s', n, re.IGNORECASE):
            return n
    # Else prefer longer name
    return max(names, key=len)


# ── Title case helpers (reused from normalize.py) ────────────────────────────────────────

_SMALL = {'or', 'and', 'de', 'com'}

def _title_word(w: str) -> str:
    if not w:
        return w
    if '-' in w:
        return '-'.join(_title_word(p) for p in w.split('-'))
    if '/' in w:
        return '/'.join(_title_word(p) for p in w.split('/'))
    for i, c in enumerate(w):
        if c.isalpha():
            return w[:i] + c.upper() + w[i+1:].lower()
    return w

def title_case_style(s: str) -> str:
    words = s.lower().split()
    return ' '.join(_title_word(w) if (i == 0 or w not in _SMALL) else w
                    for i, w in enumerate(words))

def title_case(s: str) -> str:
    return ' '.join(_title_word(w) for w in s.split())

MEDAL_MAP = {'OURO': 'Ouro', 'PRATA': 'Prata', 'BRONZE': 'Bronze',
             'Ouro': 'Ouro', 'Prata': 'Prata', 'Bronze': 'Bronze'}
MEDAL_ORDER = {'Ouro': 0, 'Prata': 1, 'Bronze': 2}


# ── CSV loading + normalisation ──────────────────────────────────────────────────────────

def load_csv(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


def normalise_row_cbc2025(r):
    style_raw = r['style'].strip()
    beer      = r['beer'].strip()
    brewery   = r['brewery'].strip()
    style = title_case_style(fix_style_cbc2025(style_raw, beer, brewery))
    return {
        'style':   style,
        'medal':   MEDAL_MAP.get(r['medal'], r['medal']),
        'beer':    title_case(beer),
        'brewery': title_case(brewery),
        'state':   r['state'].strip().upper(),
    }


# ── Blumenau 2025 style normalisation ────────────────────────────────────────────────────
# Blumenau 2025 used short Portuguese-only names; map them to the long canonical form used
# in all other contests/years.

# Short Madeira Brasileira form → long canonical form (with English subtitle)
_MADEIRA_MAP = {
    'Cerveja com Madeira Brasileira':              'Cerveja com Madeira Brasileira (Brazilian Wood- and Barrel-Aged Beer)',
    'Cerveja Experimental com Madeira Brasileira': 'Cerveja Experimental com Madeira Brasileira (Experimental Brazilian Wood- and Barrel-Aged Beer)',
    'Cerveja Ácida com Madeira Brasileira':        'Cerveja Ácida com Madeira Brasileira (Brazilian Wood- and Barrel-Aged Sour Beer)',
}

# Blumenau 2025 uses "German Doppelbock", CBC uses "German-Style Doppelbock".
# Insert "-Style" after each of these known prefixes when not already present.
_STYLE_PREFIXES = (
    'American', 'Bamberg', 'Belgian', 'British', 'Classic Australian',
    'Classic English', 'Classic French', 'Contemporary American', 'Contemporary',
    'German', 'International', 'New Zealand', 'South German', 'Traditional German',
    'West Coast',
)
# Build a regex: match "^(prefix) (?!-Style )" to find and fix missing "-Style"
_PREFIX_RE = re.compile(
    r'^(' + '|'.join(re.escape(p) for p in sorted(_STYLE_PREFIXES, key=len, reverse=True)) + r') (?!-Style\b)',
    re.IGNORECASE,
)

def _insert_style_suffix(style: str) -> str:
    """Convert 'German Doppelbock' → 'German-Style Doppelbock' etc."""
    m = _PREFIX_RE.match(style)
    if m:
        prefix = style[:m.end(1)]
        rest   = style[m.end(1)+1:]   # +1 to skip the space
        return f'{prefix}-Style {rest}'
    return style


def normalise_blumenau2025_style(raw: str) -> str:
    """Apply all Blumenau 2025 style normalisations."""
    s = title_case_style(raw.strip())
    # 1. Fix missing "-Style" suffix
    s = _insert_style_suffix(s)
    # 2. Map short Madeira Brasileira names to canonical long form
    s = _MADEIRA_MAP.get(s, s)
    return s


def normalise_row_blumenau2025(r):
    return {
        'style':   normalise_blumenau2025_style(r['style'].strip()),
        'medal':   MEDAL_MAP.get(r['medal'], r['medal']),
        'beer':    title_case(r['beer'].strip()),
        'brewery': title_case(r['brewery'].strip()),
        'state':   r['state'].strip().upper(),
    }


def normalise_row_2026(r):
    return {
        'style':   r['style'].strip(),   # already normalised by normalize.py
        'medal':   MEDAL_MAP.get(r['medal'], r['medal']),
        'beer':    r['beer'].strip(),
        'brewery': r['brewery'].strip(),
        'state':   r['state'].strip().upper(),
    }


def normalise_row_bbc2025(r):
    raw = title_case_style(r['style'].strip())
    style = BBC_STYLE_MAP.get(raw, raw)
    return {
        'style':   style,
        'medal':   MEDAL_MAP.get(r['medal'], r['medal']),
        'beer':    r['beer'].strip(),
        'brewery': r['brewery'].strip(),
        'state':   r['state'].strip().upper(),
    }


# ── Build canonical brewery name map ────────────────────────────────────────────────────

def build_brewery_name_map(all_rows_by_contest_year):
    """
    Returns dict: brewery_key -> canonical_display_name

    Logic: collect all (key, display_name) pairs from all datasets.
    For each key, pick the best display name (prefer 'Cervejaria X', else longest).
    """
    key_to_names = defaultdict(set)   # key -> set of display names seen
    for rows in all_rows_by_contest_year:
        for r in rows:
            b = r['brewery']
            k = brewery_key(b)
            if k:
                key_to_names[k].add(b)

    result = {}
    for k, names in key_to_names.items():
        names = list(names)
        # Prefer "Cervejaria X" form
        cand = [n for n in names if re.match(r'^Cervejaria\s', n, re.IGNORECASE)]
        if cand:
            result[k] = max(cand, key=len)
        else:
            result[k] = max(names, key=len)
    return result


def canonicalise_brewery(name: str, name_map: dict) -> str:
    k = brewery_key(name)
    return name_map.get(k, name)


# ── Build results.json ────────────────────────────────────────────────────────────────────

def build_results():
    # Load all CSVs
    rows_cbc25  = [normalise_row_cbc2025(r)        for r in load_csv(BASE / 'cbc-2025-results.csv')]
    rows_blu25  = [normalise_row_blumenau2025(r)    for r in load_csv(BASE / 'concurso-brasileiro-de-cervejas-2025-results.csv')]
    rows_cbc26  = [normalise_row_2026(r)            for r in load_csv(BASE / 'cbc-2026-results.csv')]
    rows_blu26  = [normalise_row_2026(r)            for r in load_csv(BASE / 'concurso-brasileiro-de-cervejas-results.csv')]
    rows_bbc25  = [normalise_row_bbc2025(r)         for r in load_csv(BASE / 'bbc-2025-results.csv')]

    # Build canonical brewery name map across all datasets
    name_map = build_brewery_name_map([rows_cbc25, rows_blu25, rows_cbc26, rows_blu26, rows_bbc25])

    # Apply canonical brewery names
    for rows in (rows_cbc25, rows_blu25, rows_cbc26, rows_blu26, rows_bbc25):
        for r in rows:
            r['brewery'] = canonicalise_brewery(r['brewery'], name_map)

    # Collect all styles
    all_styles = sorted(
        set(r['style'] for r in rows_cbc25 + rows_blu25 + rows_cbc26 + rows_blu26 + rows_bbc25),
        key=str.lower
    )

    # Build data dict: style -> {cbc: {year: [entries]}, blumenau: {year: [entries]}, bbc: {year: [entries]}}
    data = {s: {'cbc': {}, 'blumenau': {}, 'bbc': {}} for s in all_styles}

    for rows, contest, year in [
        (rows_cbc25,  'cbc',       '2025'),
        (rows_blu25,  'blumenau',  '2025'),
        (rows_cbc26,  'cbc',       '2026'),
        (rows_blu26,  'blumenau',  '2026'),
        (rows_bbc25,  'bbc',       '2025'),
    ]:
        rows_sorted = sorted(rows, key=lambda r: (r['style'].lower(), MEDAL_ORDER.get(r['medal'], 9)))
        for r in rows_sorted:
            style = r['style']
            if style not in data:
                data[style] = {'cbc': {}, 'blumenau': {}, 'bbc': {}}
            d = data[style][contest]
            if year not in d:
                d[year] = []
            d[year].append({
                'medal':   r['medal'],
                'beer':    r['beer'],
                'brewery': r['brewery'],
                'state':   r['state'],
            })

    result = {
        'years':    ['2025', '2026'],
        'contests': {
            'cbc':      'CBC — Concurso Brasileiro de Cervejas',
            'blumenau': 'Concurso Brasileiro de Cervejas de Blumenau',
            'bbc':      'Brasil Beer Cup',
        },
        'styles': all_styles,
        'data':   data,
    }

    out = BASE / 'results.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    # Stats
    styles_cbc25  = sum(1 for s in all_styles if data[s]['cbc'].get('2025'))
    styles_blu25  = sum(1 for s in all_styles if data[s]['blumenau'].get('2025'))
    styles_cbc26  = sum(1 for s in all_styles if data[s]['cbc'].get('2026'))
    styles_blu26  = sum(1 for s in all_styles if data[s]['blumenau'].get('2026'))
    styles_bbc25  = sum(1 for s in all_styles if data[s]['bbc'].get('2025'))
    total_entries = sum(len(e) for s in all_styles for c in data[s].values() for e in c.values())

    print(f'results.json written ({out.stat().st_size // 1024}KB, {len(all_styles)} styles)')
    print(f'  CBC 2025:      {len(rows_cbc25)} entries, {styles_cbc25} styles')
    print(f'  Blumenau 2025: {len(rows_blu25)} entries, {styles_blu25} styles')
    print(f'  CBC 2026:      {len(rows_cbc26)} entries, {styles_cbc26} styles')
    print(f'  Blumenau 2026: {len(rows_blu26)} entries, {styles_blu26} styles')
    print(f'  BBC 2025:      {len(rows_bbc25)} entries, {styles_bbc25} styles')
    print(f'  Total entries: {total_entries}')
    print(f'  Canonical brewery names: {len(name_map)}')

    # Cross-check brewery matches per year
    for year in ('2025', '2026'):
        contests_year = [k for k in ('cbc', 'blumenau', 'bbc') if any(data[s][k].get(year) for s in all_styles)]
        brew_sets = {}
        for c in contests_year:
            brew_sets[c] = {e['brewery'].lower() for s in all_styles for e in data[s][c].get(year, [])}
        if len(brew_sets) >= 2:
            keys = list(brew_sets)
            both = brew_sets[keys[0]] & brew_sets[keys[1]]
            print(f'  {year}: breweries in {keys[0]}∩{keys[1]} = {len(both)}', end='')
            if len(keys) > 2:
                both2 = brew_sets[keys[0]] & brew_sets[keys[2]]
                print(f', {keys[0]}∩{keys[2]} = {len(both2)}', end='')
                both3 = brew_sets[keys[1]] & brew_sets[keys[2]]
                print(f', {keys[1]}∩{keys[2]} = {len(both3)}', end='')
            print()


if __name__ == '__main__':
    build_results()
