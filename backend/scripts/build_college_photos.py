"""Campus photos for the colleges page, from Wikimedia Commons (free licenses only).

Each school's Wikidata item is found by its College Scorecard UNITID (Wikidata P1771, the IPEDS id).
The photo is the item's image (P18). A few schools without one use their Wikipedia lead photo (KEEP_WIKIPEDIA).
Joey, 2026-10-16: Commons photos with a credit line, no logos. COMMONS_PICK adds hand-checked photos from
the school's Commons category. REJECT holds the photos a person looked at and
dropped (logos, signs, old postcards, a group photo, weak shots, another campus).

Writes 720 px WebP files to frontend/public/college-photos/<program-id>.webp and the credits to
frontend/app/home/components/collegePhotos.ts. Needs sips (macOS) and cwebp.

    python3 backend/scripts/build_college_photos.py            # stops if the set of photos would change
    python3 backend/scripts/build_college_photos.py --accept   # after a person looked at the new photos
"""
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / 'backend/data/college_scorecard_2026.json'
OUT_DIR = ROOT / 'frontend/public/college-photos'
OUT_TS = ROOT / 'frontend/app/home/components/collegePhotos.ts'
OUT_IDS = ROOT / 'frontend/lib/college-photo-ids.json'  # the asset rule serves only these ids
UA = {'User-Agent': 'SPARQRecruit/1.0 (joey@gmtm.com) campus photo lookup'}
FREE = re.compile(r'^(CC BY(-SA)? [0-9.]+|CC0|Public domain|No restrictions|Attribution)$')
KEEP_WIKIPEDIA = {
    'Administration_with_North_Lawn_at_Murray_State_College.jpg', 'Alexandria-College-2021.jpg', 'Cottey_College_Main_Hall.jpg',
    'CumberlandCC_campus.jpg', 'OKWU_Campus.jpg', 'Parmenter_Hall_at_Baker_in_Kansas_by_Ian_Ballinger.jpg', 'Simpson_University_(cropped).jpg',
}
# Hand-picked from the school's Commons category (Wikidata P373) when it has no usable P18. Overrides REJECT.
COMMONS_PICK = {
    'bishop-state-community-college': 'Bishop State Business Technology Center May 2012.jpg',
    'camden-county-college': 'Ariel Photograph Camden County College 2013.jpg',
    'campbellsville-university': 'Administration Building, Campbellsville University.jpg',
    'college-of-saint-mary': 'College of Saint Mary main drive.jpg',
    'daytona-state-college': 'Daytona Beach State College01.jpg',
    'harford-community-college': 'Edgewood Hall.jpg',
    'indiana-wesleyan-university': 'Iwufountainandjacksonlibrary.jpg',
    'life-university': 'Drs Sid E and Nell K Williams Library entrance, Marietta GA.jpg',
    'manhattan-university': 'Horan Hall.jpg',
    'marywood-university': 'Marywood University Arboretum - 029.jpg',
    'mercyhurst-university': 'Mercyhurst University entry gate in September 2024.jpg',
    'midway-university': 'Historic Pinkerton Hall in Summer 2019.jpg',
    'millikin-university': 'Kirkland Fine Arts Center.jpg',
    'mount-st-mary-s-university': 'Bradley Hall.jpg',
    'penn-state-schuylkill': 'Administration Bldg at Penn State Schuylkill 01.JPG',
    'thomas-university': 'Birdwood, Forbes Hall, Thomas University, Thomasville, GA, US.jpg',
}
REJECT = {
    'albright-college', 'chowan-university', 'defiance-college', 'millsaps-college', 'texas-wesleyan-university',  # old black-and-white or postcard
    'cairn-university', 'indiana-wesleyan-university', 'manhattan-university', 'milligan-university', 'mississippi-valley-state-university',
    'mount-mary-university', 'mount-st-mary-s-university', 'point-university',  # a sign with the logo
    'life-university',  # a group photo
    'college-of-dupage', 'franciscan-university-of-steubenville', 'midland-university',  # weak shots
    'dallas-college-richland',  # Dallas College's photo shows the El Centro campus
}


def get(url):
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)


def clean(text):
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html.unescape(text or ''))).strip()
    text = re.sub(r'^No machine-readable author provided\. (\S+?)(~\w+)? assumed.*$', r'\1', text)
    text = re.sub(r'^This photo was taken by (?:participant/team )?(\S+) as part of .*$', r'\1', text)
    return text if len(text) <= 60 else text[:57].rstrip() + '…'


def main():
    programs = json.loads(SCORECARD.read_text())['programs']
    by_unitid = {}
    for pid, row in programs.items():
        if row.get('unitid') and not row.get('whole_system'):
            by_unitid.setdefault(str(row['unitid']), []).append(pid)
    values = ' '.join(f'"{u}"' for u in by_unitid)
    query = f'SELECT ?u ?item ?img WHERE {{ VALUES ?u {{ {values} }} ?item wdt:P1771 ?u . OPTIONAL {{ ?item wdt:P18 ?img }} }}'
    rows = get('https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(query))['results']['bindings']
    items, images = {}, {}
    for b in rows:
        items[b['u']['value']] = b['item']['value'].rsplit('/', 1)[1]
        if 'img' in b:
            images.setdefault(b['u']['value'], []).append(urllib.parse.unquote(b['img']['value'].rsplit('/', 1)[1]))
    pick = {}
    for u, names in images.items():
        names = sorted(names)  # the query's order is not stable
        jpgs = [n for n in names if n.rsplit('.', 1)[-1].lower() in ('jpg', 'jpeg')]
        pick[u] = (jpgs or names)[0]
    # Wikipedia lead photos (free only) for items with no P18; only the hand-checked ones are kept.
    missing = [items[u] for u in items if u not in images]
    titles = {}
    for i in range(0, len(missing), 50):
        for q, e in get('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=sitelinks&sitefilter=enwiki&ids=' + '|'.join(missing[i:i + 50]))['entities'].items():
            if e.get('sitelinks', {}).get('enwiki'):
                titles[q] = e['sitelinks']['enwiki']['title']
    lead = {}
    names = list(titles.values())
    for i in range(0, len(names), 40):
        r = get('https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&piprop=name&pilicense=free&redirects=1&titles=' + urllib.parse.quote('|'.join(names[i:i + 40])))['query']
        back = {n['to']: n['from'] for n in r.get('redirects', []) + r.get('normalized', [])}
        for p in r['pages'].values():
            if p.get('pageimage') in KEEP_WIKIPEDIA:
                lead[back.get(p['title'], p['title'])] = p['pageimage'].replace('_', ' ')
    for u, q in items.items():
        if u not in pick and titles.get(q) in lead:
            pick[u] = lead[titles[q]]

    files = sorted(set(pick.values()) | set(COMMONS_PICK.values()))
    info = {}
    for i in range(0, len(files), 40):
        r = get('https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=960&titles='
                + urllib.parse.quote('|'.join('File:' + f for f in files[i:i + 40])))['query']
        back = {n['to']: n['from'] for n in r.get('normalized', [])}
        for p in r['pages'].values():
            if 'imageinfo' not in p:
                continue
            ii, meta = p['imageinfo'][0], p['imageinfo'][0].get('extmetadata', {})
            value = lambda k: meta.get(k, {}).get('value', '')
            info[back.get(p['title'], p['title'])[5:]] = {
                'thumb': ii['thumburl'], 'page': ii['descriptionurl'], 'license': clean(value('LicenseShortName')),
                'license_url': re.sub(r'^http://', 'https://', value('LicenseUrl')) or None, 'author': clean(value('Artist')) or 'Wikimedia Commons',
                'restrictions': value('Restrictions'),
            }

    chosen = {pid: name for u, name in pick.items() for pid in by_unitid[u] if pid not in REJECT}
    chosen.update(COMMONS_PICK)
    metas = {}
    for pid, name in sorted(chosen.items()):
        meta = info.get(name) or info.get(name.replace('_', ' '))
        if not meta or not FREE.match(meta['license']) or re.search(r'trademarked|insignia', meta['restrictions']):
            print('skipped', pid, name)
            continue
        metas[pid] = meta
    # Wikidata edits change P18. A new or changed photo needs a person to look at it first.
    old = json.loads(OUT_TS.read_text().split(' = ', 1)[1]) if OUT_TS.exists() else {}
    changed = sorted(pid for pid in set(old) | set(metas) if old.get(pid, {}).get('page') != metas.get(pid, {}).get('page'))
    if changed and '--accept' not in sys.argv:
        for pid in changed:
            print('changed', pid, old.get(pid, {}).get('page'), '->', metas.get(pid, {}).get('page'))
        sys.exit('The photo set changed. Look at the new photos, then run again with --accept.')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    credits = {}
    with tempfile.TemporaryDirectory() as tmp:
        for pid, meta in metas.items():
            src, jpg = Path(tmp) / f'{pid}.src', Path(tmp) / f'{pid}.jpg'
            src.write_bytes(urllib.request.urlopen(urllib.request.Request(meta['thumb'], headers=UA), timeout=60).read())
            subprocess.run(['sips', '-s', 'format', 'jpeg', str(src), '--out', str(jpg)], check=True, capture_output=True)
            subprocess.run(['cwebp', '-quiet', '-q', '62', '-resize', '720', '0', str(jpg), '-o', str(OUT_DIR / f'{pid}.webp')], check=True)
            credits[pid] = {k: meta[k] for k in ('author', 'license', 'license_url', 'page')}
            time.sleep(0.2)
    for stale in OUT_DIR.glob('*.webp'):
        if stale.stem not in credits:
            stale.unlink()
    OUT_TS.write_text(
        '// Generated by backend/scripts/build_college_photos.py. Do not edit by hand.\n'
        '// Campus photos from Wikimedia Commons (free licenses), served from /college-photos/<id>.webp.\n'
        'export interface PhotoCredit { author: string; license: string; license_url: string | null; page: string }\n'
        f'export const PHOTOS: Record<string, PhotoCredit> = {json.dumps(credits, indent=1, ensure_ascii=False, sort_keys=True)}\n')
    OUT_IDS.write_text(json.dumps(sorted(credits), indent=0) + '\n')
    print(f'{len(credits)} photos of {len(programs)} programs')


if __name__ == '__main__':
    main()
