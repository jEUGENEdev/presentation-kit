#!/usr/bin/env python3
"""Build one offline HTML file. Standard library only; works from any cwd."""
from __future__ import annotations
import argparse
import base64
import html
import json
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def escape(value):
    return html.escape(str(value), quote=True)

def load_data(root=ROOT):
    data = json.loads((root / 'data/deck.json').read_text(encoding='utf-8'))
    data['notes'] = json.loads((root / 'data/notes.json').read_text(encoding='utf-8'))
    validate_data(data)
    return data

def validate_data(data):
    appearance=data.get('appearance',{})
    if appearance.get('default_theme','light') not in {'light','dark'}:
        raise ValueError('Theme must be light or dark')
    traveler=appearance.get('traveler',{})
    characters=traveler.get('characters',{})
    if characters:
        if traveler.get('default') not in characters or any(v not in characters for v in traveler.get('per_slide',{}).values()):
            raise ValueError('Unknown traveler character')
        if any(not isinstance(g,str) or not 1 <= len(g) <= 8 for g in characters.values()):
            raise ValueError('Traveler glyphs must be short text')
    if len(data['team_members']) != 5:
        raise ValueError('Expected five contributors')
    if len(data['heuristics']) != 6 or sum(x['weight'] for x in data['heuristics']) != 100:
        raise ValueError('Six heuristic weights must sum to 100')
    keys = {h['key'] for h in data['heuristics']}
    if len(keys) != 6 or any(not 0 < h['weight'] <= 100 for h in data['heuristics']):
        raise ValueError('Heuristic keys must be unique and weights positive')
    if not data['cases']:
        raise ValueError('At least one scoring example is required')
    for item in data['cases'] + data['results']:
        if not isinstance(item['score'], int) or not 0 <= item['score'] <= 100:
            raise ValueError('Scores must be integer values between 0 and 100')
    if any(not set(c['hits']) <= keys for c in data['cases']):
        raise ValueError('Unknown heuristic in scoring case')
    counts = {g:sum(r['group']==g for r in data['results']) for g in ['flagged','organic','viral']}
    if counts != {'flagged':5,'organic':9,'viral':2}:
        raise ValueError('This deck expects the complete 16-repository source sample')
    if len({r['repo'] for r in data['results']}) != len(data['results']):
        raise ValueError('Duplicate result repository')
    for key in ['repository_url','landing_url']:
        if data.get(key) and not data[key].startswith('https://'):
            raise ValueError(f'{key} must be an HTTPS URL')
    if data.get('qr_asset') and not data.get('landing_url'):
        raise ValueError('Set landing_url together with qr_asset')

def asset_uri(path: Path):
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

def level(score):
    return 'critical' if score >= 85 else 'high' if score >= 60 else 'medium' if score >= 30 else 'low'

def qr_block(data, root):
    url, asset = data.get('landing_url'), data.get('qr_asset')
    if asset:
        path = (root / asset).resolve()
        if not path.is_relative_to((root / 'assets').resolve()):
            raise ValueError('QR asset must be inside assets/')
        if path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
            raise ValueError('Use a raster QR image')
        visual = f'<img src="{asset_uri(path)}" alt="QR-код: открыть лендинг Star Guard">'
    else:
        visual = '<span class="qr-placeholder">QR</span>'
    text = 'Попробуйте Star Guard' if url else 'Место для QR на лендинг'
    note = 'Открыть лендинг' if url else 'Адрес будет добавлен перед выступлением'
    inner = f'{visual}<p>{text}<small>{note}</small></p>'
    return f'<a class="qr-block" href="{escape(url)}" target="_blank" rel="noopener noreferrer">{inner}</a>' if url else f'<div class="qr-block">{inner}</div>'

def fragments(data, root):
    members=[]
    colors=['#3557eb','#7945e8','#dc347a','#078659','#b7740b']
    for i,m in enumerate(data['team_members']):
        name=escape(m['name']) if m['name'] else '<span class="unfilled">Имя Фамилия</span>'
        role=escape(m['role']) if m['role'] else '<span class="unfilled">Зона ответственности</span>'
        cells='<i></i>'*17
        members.append(f'<article class="member reveal" style="--member-color:{colors[i]}"><span class="member-index">CONTRIBUTOR / 0{i+1}</span><div class="avatar" aria-hidden="true">{i+1:02}</div><h3>{name}</h3><p class="handle">@{escape(m["handle"])}</p><p class="role">{role}</p><div class="mini-grid" aria-hidden="true">{cells}</div></article>')
    heuristics=[]
    for h in data['heuristics']:
        heuristics.append(f'<div class="heuristic {"" if h["active"] else "later"}" data-key="{escape(h["key"])}"><div><code>{escape(h["key"])}</code><small>{escape(h["label"])}</small></div><div class="weight-track" aria-hidden="true"><i style="--weight:{h["weight"]/30*100:.2f}%"></i></div><b>{h["weight"]}%</b></div>')
    buttons=''.join(f'<button data-case="{i}" aria-pressed="{str(i==0).lower()}">{escape(c["repo"].split("/")[-1])}</button>' for i,c in enumerate(data['cases']))
    def rows(group):
        result=''
        for r in data['results']:
            if r['group'] != group: continue
            color={'low':'#078659','medium':'#b7740b','high':'#dc651b','critical':'#dc347a'}[level(r['score'])]
            result+=f'<tr data-result="{escape(group)}"><td>{escape(r["repo"])}</td><td data-level="{level(r["score"])}" style="color:{color}">{r["score"]}</td></tr>'
        return result
    header='<thead><tr><th scope="col">Репозиторий</th><th scope="col">Score</th></tr></thead>'
    tables=f'<table><caption>НАКРУТКА ПО РАЗМЕТКЕ КОМАНДЫ / 5</caption>{header}<tbody>{rows("flagged")}<tr class="group-row"><td colspan="2">ВИРУСНЫЙ РОСТ / 2 ЛОЖНЫХ СИГНАЛА</td></tr>{rows("viral")}</tbody></table><table><caption>ОРГАНИКА БЕЗ ВИРУСНОЙ ВОЛНЫ / 9</caption>{header}<tbody>{rows("organic")}</tbody></table>'
    loads=''.join(f'<div class="load-row {escape(r["status"])}"><div><span>{r["threads"]} {"поток" if r["threads"]==1 else "потока"}</span><b>{r["seconds"]} с</b></div><div class="load-track" aria-hidden="true"><i style="--load:{r["seconds"]/500*100:.1f}%"></i></div><p>{escape(r["comment"])}</p></div>' for r in data['load'])
    labels={'star':'Звезда','shield':'Щит','bug':'Жучок','owl':'Сова','packet':'Пакет данных'}
    traveler_options='<option value="auto">По слайду</option>'+''.join(f'<option value="{escape(k)}">{escape(labels.get(k,k))}</option>' for k in data.get('appearance',{}).get('traveler',{}).get('characters',{'star':'★'}))
    out={'TRAVELER_OPTIONS':traveler_options,'TEAM_MEMBERS':''.join(members),'HEURISTICS':''.join(heuristics),'CASE_BUTTONS':buttons,'RESULT_TABLES':tables,'LOAD_ROWS':loads,'QR_COVER':qr_block(data,root),'QR_FINAL':qr_block(data,root)}
    for key in ['TITLE','EVENT','TEAM','TEST_DATE','REPOSITORY_URL']:
        out[key]=escape(data[key.lower()])
    for name in ['popup','mcp','report']:
        out[name.upper()]=asset_uri(root / 'assets/screenshots' / f'{name}.jpg')
    for name in ['browser','bot','repo','db','archive']:
        svg=(root / 'assets' / f'{name}.svg').read_text()
        out['ICON_'+name.upper()]=svg
    return out

def substitute(text, values):
    def replace(match):
        key=match[1]
        if key not in values: raise ValueError(f'Unresolved token: {key}')
        return values[key]
    return re.sub(r'\{\{([A-Z_]+)\}\}',replace,text)

def build(output=None, root=ROOT):
    data=load_data(root)
    values=fragments(data,root)
    slides=substitute((root/'src/slides.html').read_text(encoding='utf-8'),values)
    slide_meta=re.findall(r'<section class="slide [^"]+" id="([^"]+)" data-chapter="([^"]+)" data-title="([^"]+)"',slides)
    if len(slide_meta)!=12 or len({s[0] for s in slide_meta})!=12:
        raise ValueError('Exactly 12 uniquely identified slides are required')
    if set(data['notes'])!={s[0] for s in slide_meta}:
        raise ValueError('Every slide needs exactly one speaker note')
    fonts=[]
    for notice in sorted((root/'assets/fonts').glob('*-OFL.txt')):
        fonts.append('/*\n'+notice.read_text(encoding='utf-8').replace('*/','* /')+'\n*/')
    for family,file in [('Onest','Onest'),('Unbounded','Unbounded'),('JetBrains Mono','JetBrainsMono')]:
        uri=asset_uri(root/'assets/fonts'/f'{file}.woff')
        fonts.append(f'@font-face{{font-family:"{family}";src:url("{uri}") format("woff");font-weight:100 900;font-display:block}}')
    values.update(SLIDES=slides,FONTS='\n'.join(fonts),CSS=(root/'src/theme.css').read_text(),JS=(root/'src/deck.js').read_text(),DATA=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026'),OVERVIEW=''.join(f'<button data-goto="{i}"><b>{i+1:02} / {ch}</b><span>{title}</span></button>' for i,(_,ch,title) in enumerate(slide_meta)))
    result=substitute((root/'src/shell.html').read_text(encoding='utf-8'),values)
    output=Path(output) if output else root/'dist/index.html'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(result,encoding='utf-8')
    print(f'Built {output.name}: {output.stat().st_size:,} bytes, {len(slide_meta)} slides')
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Output path (default: dist/index.html)')
    args=parser.parse_args()
    try: build(args.output)
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as exc: parser.exit(1,f'Build failed: {exc}\n')
