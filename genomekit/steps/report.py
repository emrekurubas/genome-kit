# Build the HTML pages from everything the steps produced:
#   index.html (hub), Genome_Report.html (plain-language main report), Doctor_Checklist.html,
#   Ancestry.html (lineages + ancestry), Variant_Effects.html (only with the effects tier).
# All pages are self-contained local files (images embedded), light/dark aware, readable on a phone.
import base64, datetime, html, json, re
from pathlib import Path
from ..util import jload, jdump
from ..report_style import css, TIP_JS
from ..kb import pgx as PGX
from ..kb.pgs import SCORES
from ..kb.haplogroups import Y as YDESC, MT as MTDESC, describe

esc = html.escape
LV = {'act': 'If prescribed', 'know': 'Good to know', 'ok': 'All fine', 'fun': 'Just interesting'}
EXTRA = '''
p.crumbs{font-size:13.5px;margin:0 0 6px}
.callout.big{font-size:16px;padding:16px 20px}.callout.big ul{margin:6px 0 0;padding-left:20px}.callout.big li{margin:6px 0}
nav.toc{font-size:14px;margin:16px 0 4px}nav.toc a{color:var(--acc)}
.item{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:10px;padding:14px 18px;margin:12px 0}
.item.act{border-left-color:var(--s2)}.item.know{border-left-color:var(--s1)}.item.ok{border-left-color:var(--ok)}.item.fun{border-left-color:var(--s3)}
.ih{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.ih h3{margin:0;font-size:17px}
.item p{margin:6px 0}.item p.find{font-size:15.5px}
.badge{font-size:11.5px;font-weight:700;border-radius:999px;padding:2px 9px;white-space:nowrap;letter-spacing:.02em}
.badge.act{background:var(--midbg);color:var(--mid)}.badge.know{background:var(--track);color:var(--s1)}.badge.ok{background:var(--okbg);color:var(--ok)}.badge.fun{background:var(--track);color:var(--s3)}
ul.fine{columns:2;column-gap:28px;margin:0;padding-left:18px}ul.fine li{break-inside:avoid;margin:4px 0}
.pages{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:12px 0}
.pcard{display:flex;flex-direction:column;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;text-decoration:none;color:var(--fg)}
.pcard:hover{border-color:var(--acc)}.pcard span{font-size:13.5px;color:var(--mut)}.pcard b{font-size:16px}
dl.gl dt{font-weight:700;margin-top:10px}dl.gl dd{margin:2px 0 0 0;color:var(--fg)}
details{margin:14px 0}
.notice{background:var(--midbg);border:1px solid var(--mid);border-left:6px solid var(--mid);border-radius:12px;padding:16px 20px;margin:20px 0 24px;font-size:15.5px}
.notice .nh{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700;color:var(--mid);margin:0 0 6px}
.notice .ni{flex:none;display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:var(--mid);color:var(--midbg);font-size:16px;font-weight:800}
.notice p{margin:6px 0}
@media print{.notice{border:2px solid #000;background:#fff;color:#000}.notice .nh{color:#000}.notice .ni{background:#000;color:#fff}}
@media (max-width:700px){ul.fine{columns:1}table.stack thead{display:none}table.stack tr{display:block;border-bottom:1px solid var(--line);padding:8px 0}table.stack td{display:block;border:0;padding:2px 0;text-align:left}table.stack td.num::before{content:'Percentile: ';font-weight:400;color:var(--mut)}}
'''
GLOSSARY = {
    'Gene': 'A stretch of DNA that is a recipe for one protein.',
    'Variant': 'A spot where people\'s DNA differs, like a one-letter spelling difference.',
    'Copy': 'You have two copies of most genes, one from each parent. “Two copies” means you inherited the variant from both parents.',
    'Percentile': 'Your position among 100 comparable people. 50 is average and 90 means higher than 90 of them.',
    'Polygenic score': 'A sum of thousands of tiny genetic nudges toward a trait or disease. Useful as a hint, never a diagnosis.',
    'HLA': 'Immune-system genes that differ a lot between people. Some types affect medicine reactions or autoimmune diseases.',
    'Metaboliser': 'How fast your body breaks down a medicine: poor, intermediate, normal or rapid.',
    'Haplogroup': 'A family of related DNA lineages, used to trace the father-line (Y chromosome) or mother-line (mitochondrial DNA) back in time.',
    'Imputation': 'Filling in DNA positions the chip didn\'t measure, using patterns from thousands of fully sequenced people. Good for common variants, unreliable for rare ones.',
}
DISCLAIMER = ('For information only. This is a research-grade reading of consumer DNA data, not a medical diagnosis, and none of it '
              'is an absolute finding. Talk to a doctor or other medical professional before acting on anything here, especially the '
              'medicine findings; they can confirm a result with a clinical test.')
# Shown at the top of every page with health content.
NOTICE = '''<aside class="notice" role="note" aria-label="Important: for information only">
<div class="nh"><span class="ni" aria-hidden="true">!</span>For information only. Not a medical diagnosis.</div>
<p>These results are <b>not absolute findings</b>. They come from a consumer DNA chip read by research software. Chips can misread DNA, especially rare variants, and most genes only nudge chances up or down. Your health also depends on family history, lifestyle and environment, which DNA does not show.</p>
<p><b>Talk to a doctor or other medical professional</b> before you act on anything here. Do not start, stop or change a medicine or treatment because of this report. A doctor can order a clinical test to confirm a result.</p>
</aside>'''


FORMAT = {'23andme': '23andMe-style', 'ancestry': 'AncestryDNA', 'csv': 'MyHeritage/FTDNA-style'}


def page(title, body, extra=''):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{css}{EXTRA}{extra}</style></head><body>{body}{TIP_JS}</body></html>')


def item_html(x):
    rows = ''.join(f'<p><b>{k}</b> {v}</p>' for k, v in [('What it is:', x.get('what', '')), ('How much it matters:', x.get('size', '')),
                                                           ('What to do:', x.get('todo', '')), ('Note:', x.get('note', ''))] if v)
    lv = x.get('level', 'know')
    return (f'<div class="item {lv}"><div class="ih"><span class="badge {lv}">{LV[lv]}</span><h3>{x["title"]}</h3></div>'
            f'<p class="find">{x["finding"]}</p>{rows}</div>')


def img64(p):
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()


def ordn(x):
    x = int(round(float(x))); return f"{x}{'th' if 10 <= x % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(x % 10, 'th')}"


# ------------------------------------------------------------------------------------------------ collect facts
def pharmcat_genes(work):
    j = jload(work / 'pharmcat' / 'input.report.json')
    if not j: return None, {}
    P = {}
    for g, x in j['genes'].items():
        rd = x.get('recommendationDiplotypes') or x.get('sourceDiplotypes') or []
        if not rd: continue
        labels = [r.get('label', '') for r in rd]
        phs = [', '.join(r.get('phenotypes') or []) for r in rd]
        known = [p for p in phs if p and 'Indeterminate' not in p and 'No Result' not in p]
        if known:
            top = max(set(known), key=known.count)
            uncertain = len(set(known)) > 1
            if known.count(top) / len(known) <= 0.5: top, uncertain = '', True
        else:
            top, uncertain = '', False
        P[g] = dict(phenotype=top, diplotype=' OR '.join(labels), uncertain=uncertain)
    return j, P


def hla_celiac(hla):
    """DQ2.5 / DQ8 copies from HLA typing (DQA1*05 + DQB1*02:01 = DQ2.5; DQB1*03:02 = DQ8)."""
    if not (hla.get('DQB1') and hla.get('DQA1')): return None
    b = [hla['DQB1']['allele1'], hla['DQB1']['allele2']]; a = [hla['DQA1']['allele1'], hla['DQA1']['allele2']]
    dq25 = min(sum(x.startswith('02:01') for x in b), sum(x.startswith('05') for x in a))
    dq8 = sum(x.startswith('03:02') for x in b)
    return dq25, dq8


def collect(ctx):
    w = ctx.work
    s = jload(w / 'sample.json'); cfg = ctx.cfg
    mk = jload(w / 'markers.json', {'items': [], 'fine': [], 'traits': [], 'check': [], 'proxies': {}})
    hla = jload(w / 'hla.json', {})
    cv = jload(w / 'clinvar.json', {'report': []})
    pgs = jload(w / 'pgs.json')
    anc = jload(w / 'ancestry.json')
    aadr = jload(w / 'ancient.json')
    mt = jload(w / 'mtdna.json', {}); y = jload(w / 'ydna.json', {})
    eff = jload(w / 'effects.json')
    _, P = pharmcat_genes(w)
    status = jload(w / 'status.json', {})

    meds, cards, normal = PGX.interpret(P or {}, hla, mk.get('proxies', {}), s['sex']) if P is not None else ([], [], [])
    if normal:
        meds.append(dict(level='ok', title='Everything else the medicine check covers', finding='Normal or typical: ' + ', '.join(normal) + '.', todo='Nothing.',
                         note='CYP2D6 (codeine, tramadol, tamoxifen, many antidepressants) cannot be read from a consumer chip.'))

    health = list(mk['items'])
    fine = list(mk['fine'])
    # HLA-based celiac item
    hc = hla_celiac(hla)
    check = list(mk.get('check', []))
    if hc:
        dq25, dq8 = hc
        if dq25 or dq8:
            what = ' and '.join(x for x in [f'{"one copy" if dq25 == 1 else "two copies"} of <b>HLA-DQ2.5</b>' if dq25 else '',
                                            f'{"one copy" if dq8 == 1 else "two copies"} of <b>HLA-DQ8</b>' if dq8 else ''] if x)
            health.append(dict(level='know', title='Autoimmune tendency: celiac-type immune genes',
                               finding=f'HLA typing found {what}, the immune-gene types that allow celiac disease (also linked to type 1 diabetes and thyroid autoimmunity).',
                               size='About 1 in 3 people carry DQ2.5 or DQ8, and only about 1 in 30 of them ever develop celiac disease. Without these types celiac disease is almost impossible.',
                               todo='Nothing now. Lasting digestive trouble, anaemia or unexplained tiredness would be a reason for a celiac blood test (tTG-IgA) while still eating gluten.'))
            check.append(dict(test='Celiac antibodies (tTG-IgA)', why='HLA-DQ2.5/DQ8 carrier', when='Only if symptoms appear', conditional=True))
        else:
            fine.append('Celiac immune types (HLA-DQ2.5, DQ8): not present, so celiac disease is very unlikely')

    # ClinVar
    rep = cv.get('report', [])
    if rep:
        for h in rep:
            hom = h['copies'] == 2
            health.append(dict(kind='clinvar', level='know', title=f'{esc(h["gene"] or "Gene")}: variant listed as disease-causing',
                               finding=f'The chip reported {"two copies" if hom else "one copy"} of a variant that ClinVar lists as <b>{esc(h["significance"].lower())}</b> for <b>{esc(h["condition"])}</b> ({esc(h["rsid"])}).',
                               what=('Many such conditions are recessive: one copy then only makes you a carrier, which matters for family planning.' if not hom else ''),
                               size=('This variant is very rare in the population. Consumer chips get rare variants wrong surprisingly often: in one study about 40% of such calls did not hold up in a clinical test. ' if h.get('likely_artifact') else '') +
                                    'Do not act on it before it is confirmed.',
                               todo='If it matters to you (symptoms, family history or family planning), ask a doctor or genetic counsellor for a clinical confirmation test.',
                               note=f'ClinVar review: {"★" * h["stars"]}{"☆" * (4 - h["stars"])}; population frequency {h["af"] * 100:.3g}%.'))
    else:
        fine.insert(0, 'No confirmed disease-causing variant among the ones the chip reads (ClinVar)')
    for u in mk.get('unread', []): fine.append(f'{u}: not read by this chip')
    roh = s.get('roh', {})
    if roh:
        fine.append({'none': 'No sign that your parents were related', 'distant': 'Some long identical stretches: parents may be distantly related (common in some communities)',
                     'close': 'Long identical stretches suggest your parents are related'}[roh['verdict']])

    # Polygenic scores
    pg_rows, pg_hl = [], []
    if pgs:
        meta = {x['id']: x for x in SCORES}
        for r in pgs['scores']:
            m = meta.get(r['id'])
            if not m or (m.get('sex') and m['sex'] != s['sex']): continue
            pct = r['pct']; inv = m.get('invert')
            if pct is None: continue
            hi, lo = pct >= 90, pct <= 10
            meaning = m.get('high') if hi else m.get('low') if lo else m.get('mid', 'Average.' if 25 <= pct <= 75 else ('Above average.' if pct > 75 else 'Below average.'))
            if m['show'] == 'summary' and (hi or lo or m.get('always')) and meaning:
                pg_hl.append(dict(label=m['label'], pct=pct, meaning=meaning, id=r['id']))
            status_ = ('in the summary above' if m['show'] == 'summary' and (hi or lo or m.get('always')) else
                       'uncertain: shifts strongly with ancestry' if r.get('ancestry_sensitive') else
                       'high, but a weak score with little practical meaning' if hi and m['strength'] == 'weak' else
                       'high' if hi else 'low' if lo else 'not remarkable')
            pg_rows.append(dict(label=m['label'], pct=pct, status=status_, id=r['id']))
            if hi and m.get('test'): check.append(dict(zip(('test', 'why', 'when'), m['test']), conditional=m.get('conditional', False)))
            if lo and m.get('test_low'): check.append(dict(zip(('test', 'why', 'when'), m['test_low'])))
        pg_hl.sort(key=lambda x: -abs(x['pct'] - 50))

    return dict(sample=s, name=cfg.get('name') or s.get('name') or '', meds=meds, cards=cards, health=health, fine=fine,
                traits=mk.get('traits', []), check=check, pgs=pgs, pg_rows=pg_rows, pg_hl=pg_hl, hla=hla, anc=anc, aadr=aadr,
                mt=mt, y=y, eff=eff, pharmcat=P, status=status, tiers=cfg.get('tiers', ['core']), clinvar=rep)


# ------------------------------------------------------------------------------------------------ text helpers
def ancestry_sentence(F):
    parts = []
    if F['aadr']:
        top = list(F['aadr']['closest_modern'].keys())[:3]
        parts.append(f'Among 260 present-day populations worldwide, your DNA is closest to <b>{esc(top[0].replace("_", " "))}</b>, then {esc(", ".join(t.replace("_", " ") for t in top[1:]))}.')
        q = F['aadr'].get('qpadm_best')
        if q: parts.append('The best-fitting ancient-DNA model: ' + ', '.join(f'{esc(k)} {v * 100:.0f}%' for k, v in q['weights'].items()) + '.')
    elif F['anc']:
        an = F['anc']
        parts.append(f'Among the 26 populations of the 1000 Genomes Project, the closest to you are <b>{esc(", ".join(an["nearest_names"][:3]))}</b>.' +
                     ('' if an.get('close_match', True) else ' You are not a close match to any of them: that reference has no Middle Eastern, Caucasus, '
                      'North African or Central Asian groups, so people with roots there land between the groups it has.'))
    hg = []
    if F['y'].get('haplogroup'): hg.append(f'father-line <b>{esc(F["y"]["haplogroup"])}</b>')
    if F['mt'].get('haplogroup'): hg.append(f'mother-line <b>{esc(F["mt"]["haplogroup"])}</b>')
    if hg: parts.append(f'Your {" and ".join(hg)} {"are" if len(hg) > 1 else "is"} described on the ancestry page.')
    if not parts: parts.append('Choose the imputation or ancient-DNA parts next time for an ancestry estimate.')
    return ' '.join(parts)


def short_version(F):
    out = []
    if F['clinvar']:
        out.append(f'<b>{len(F["clinvar"])} variant{"s" if len(F["clinvar"]) > 1 else ""} listed as disease-causing</b> came up. Consumer chips often get such rare calls wrong, so treat them as “to be confirmed”, not as a diagnosis.')
    else:
        out.append('<b>No serious inherited disease variant was found</b> among the ones this chip can read, including the common founder mutations checked (blood clotting, haemochromatosis, FMF, sickle cell and others).')
    act = [m for m in F['meds'] if m['level'] == 'act']
    if act:
        names = ', '.join(f'<b>{strip_tags(m["title"])}</b>' for m in act[:6])
        out.append(f'<b>Medicines: the most useful part.</b> Some medicines need a different choice or dose for you: {names}. Show the medicine card to a doctor or pharmacist if any of these comes up.')
    elif F['pharmcat'] is not None:
        out.append('<b>Medicines:</b> none of the medicine genes this chip can read needs a change of medicine or dose.')
    for h in F['health']:
        if h['level'] in ('act', 'know') and h.get('kind') != 'clinvar' and len(out) < 5:
            out.append(f'<b>{h["title"]}:</b> {strip_tags(h["finding"])}')
    hi = [p for p in F['pg_hl'] if p['pct'] >= 90]
    if hi:
        out.append('<b>Polygenic scores</b> are notably high for ' + ', '.join(f'{esc(p["label"].lower())} ({ordn(p["pct"])} percentile)' for p in hi[:4]) +
                   '. These shift chances a little; they are not diagnoses.')
    out.append('<b>Ancestry:</b> ' + ancestry_sentence(F))
    return out


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s)


# ------------------------------------------------------------------------------------------------ pages
def main_report(ctx, F):
    name = F['name']
    today = datetime.date.today().isoformat()
    sv = ''.join(f'<li>{b}</li>' for b in short_version(F))
    sec = lambda sid, title, intro, items: (f'<h2 id="{sid}">{title}</h2>' + (f'<p class="mut">{intro}</p>' if intro else '') + ''.join(item_html(x) for x in items)) if items else ''
    meds_intro = ('Your genes affect how fast your body processes some medicines, and a few gene types raise the risk of a bad reaction. '
                  'Doctors use official guidelines (CPIC) for this. None of it means you should stop a medicine you already take without talking to your doctor.')
    health = sorted(F['health'], key=lambda x: {'act': 0, 'know': 1, 'ok': 2, 'fun': 3}[x['level']])
    # polygenic section
    if F['pgs']:
        hl = ''.join(f'<tr><td>{esc(p["label"])}</td><td class=num><b>{p["pct"]:.0f}</b></td><td>{p["meaning"]}</td></tr>' for p in F['pg_hl'])
        full = ''.join(f'<tr><td>{esc(r["label"])}</td><td class=num>{r["pct"]:.0f}</td><td>{esc(r["status"])}</td></tr>' for r in sorted(F['pg_rows'], key=lambda r: -r['pct']))
        ref = F['pgs'].get('reference_note', '')
        pgs_html = f'''<h2 id="pgs">Polygenic scores: small nudges from many genes</h2>
<p>A polygenic score adds up thousands of tiny genetic effects. The <b>percentile</b> compares you with 100 people of similar ancestry: 90 means your score is higher than 90 of them. Even at the 90th percentile the chance is usually only about <b>1.3–2 times the average</b> for strong scores, and 1.1–1.4 times for weaker ones. Most people with high scores never get the condition, and many people with low scores do.</p>
<div class="panel tw"><table class="stack"><thead><tr><th>Trait</th><th class=num>Percentile</th><th>What it means</th></tr></thead><tbody>{hl}</tbody></table></div>
<p class="mut small">{esc(ref)}</p>
<details><summary>For the curious: all {len(F["pg_rows"])} scores</summary><div class="tw"><table><thead><tr><th>Trait</th><th class=num>Percentile</th><th>Status</th></tr></thead><tbody>{full}</tbody></table></div></details>'''
    else:
        pgs_html = ('<h2 id="pgs">Polygenic scores</h2><p class="mut">Not computed this time. They need the “Imputation, polygenic scores and HLA typing” part; '
                    'run the kit again and choose it to add them (everything done so far is kept).</p>')
    fine = ''.join(f'<li>{esc(b) if "<" not in b else b}</li>' for b in F['fine'])
    nexts = [f'<b>Keep the medicine card handy</b> (on the doctor checklist). Show it to a doctor or pharmacist when relevant. A clinical pharmacogenetic test can confirm it.'] if F['cards'] else []
    routine = [c['test'] for c in F['check'] if not c.get('conditional')]
    if routine: nexts.append('<b>Routine check-up tests that cover the findings above:</b> ' + esc(', '.join(dict.fromkeys(routine))) + '.')
    if F['y'].get('haplogroup'): nexts.append(f'<b>For fun:</b> a Y-chromosome sequencing test would pin down your father-line branch below {esc(F["y"]["haplogroup"])}.')
    missing = [t for t in ('impute', 'ancient', 'effects') if t not in F['tiers']]
    if missing:
        from ..refs import TIERS
        nexts.append('<b>More analyses are available:</b> run the kit again and choose ' + ', '.join(f'“{TIERS[t]["title"]}”' for t in missing) + '.')
    links = [('Doctor_Checklist.html', 'Doctor checklist', 'Printable list of check-up tests and the medicine card.'),
             ('Ancestry.html', 'Ancestry and family lines', 'Your father-line and mother-line, and where your ancestors came from.')]
    if F['eff']: links.append(('Variant_Effects.html', 'Small changes in your genes', 'Predicted effects of the protein-changing variants you carry.'))
    linkhtml = ''.join(f'<a class="pcard" href="{f}"><b>{esc(t)} ↗</b><span>{esc(d)}</span></a>' for f, t, d in links)
    title = f'{name}, here is what your DNA says' if name else 'Here is what your DNA says'
    s = F['sample']
    body = f'''<main>
<p class="crumbs"><a href="index.html">← All reports</a></p>
<div class="kicker">{esc(name + " · " if name else "")}{esc(FORMAT.get(s["format"], s["format"]))} raw data · analysed privately on this computer · {today}</div>
<h1>{esc(title)}</h1>
<p class="lede">This report reads your raw DNA data with up-to-date research tools. Everything was computed on this computer and nothing was uploaded. Most of what is here is reassuring or simply interesting. The most useful part is usually about medicines.</p>
{NOTICE}
<div class="callout big"><h2 style="margin:0 0 8px;font-size:20px">The short version</h2><ul>{sv}</ul></div>
<p class="mut small">How to read this page: every finding has a label. <span class="badge act">If prescribed</span> means it matters if you are ever given that medicine (or needs a doctor's look); <span class="badge know">Good to know</span> means real but usually small, often with nothing to do; <span class="badge ok">All fine</span> means checked and normal; <span class="badge fun">Just interesting</span> is not about health at all.</p>
<nav class="toc"><a href="#meds">Medicines</a> · <a href="#health">Health</a> · <a href="#pgs">Polygenic scores</a> · <a href="#fine">Checked and fine</a> · <a href="#ancestry">Ancestry</a> · <a href="#traits">Traits</a> · <a href="#next">Next steps</a> · <a href="#words">Words explained</a></nav>
{sec('meds', 'Medicines: how your body handles some drugs', meds_intro, F['meds'])}
{sec('health', 'Health findings', 'These are the specific gene findings with the best scientific support. Each one shifts a chance; none decides anything on its own. Lifestyle and regular check-ups matter more than any of these genes.', health) or '<h2 id="health">Health findings</h2><p>Nothing specific stood out among the curated markers.</p>'}
{pgs_html}
<h2 id="fine">Checked and fine</h2><p class="mut">These were looked for specifically and came back normal.</p><div class="panel"><ul class="fine">{fine}</ul></div>
<h2 id="ancestry">Ancestry in a few lines</h2><p>{ancestry_sentence(F)}</p><div class="pages">{linkhtml}</div>
{sec('traits', 'Fun traits', '', F['traits'])}
<h2 id="next">Next steps (all optional)</h2><div class="panel"><ul>{''.join(f"<li>{n}</li>" for n in nexts) or "<li>Nothing specific.</li>"}</ul></div>
<h2 id="words">Words explained</h2><div class="panel"><dl class="gl">{''.join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in GLOSSARY.items())}</dl></div>
<div class="callout small">{DISCLAIMER}</div>
<footer><a href="index.html">← All reports</a> · Made privately on this computer with genome-kit.</footer>
</main>'''
    (ctx.out / 'Genome_Report.html').write_text(page(f'{name + " " if name else ""}Genome Report', body))


def checklist(ctx, F):
    today = datetime.date.today().isoformat()
    seen, routine, cond = set(), [], []
    for c in F['check']:
        if c['test'] in seen: continue
        seen.add(c['test']); (cond if c.get('conditional') else routine).append(c)
    if not any('blood count' in c['test'].lower() for c in routine):
        routine.append(dict(test='Complete blood count', why='General baseline (thalassaemia and most sickle variants are not on the chip)', when='With check-ups'))

    def table(cols, rows, box=True):
        head = ''.join(f'<th>{h}</th>' for h in cols)
        body = ''.join('<tr>' + ('<td class="box" aria-hidden="true">☐</td>' if box else '') + ''.join(f'<td data-l="{h}">{c}</td>' for h, c in zip(cols, r)) + '</tr>' for r in rows)
        return f'<div class="panel tw"><table class="ck"><thead><tr>{"<th></th>" if box else ""}{head}</tr></thead><tbody>{body}</tbody></table></div>'
    secs = '<h2>Tests at the next check-up</h2>' + table(['Test', 'Why', 'How often'], [(esc(c['test']), esc(c['why']), esc(c['when'])) for c in routine])
    if cond:
        secs += ('<h2>Only if symptoms appear</h2><p class="mut">Nothing needs testing now; these are the tests to ask for if matching symptoms show up.</p>' +
                 table(['Test', 'Background', 'When'], [(esc(c['test']), esc(c['why']), esc(c['when'])) for c in cond], box=False))
    if F['cards']:
        secs += ('<h2>Medicine card</h2><p class="mut">Show this to a doctor or pharmacist whenever one of these medicines comes up.</p>' +
                 table(['Medicine', 'What to do', 'Gene result'], F['cards'], box=False))
    else:
        secs += '<h2>Medicine card</h2><p>No medicine-gene result needs a change of medicine or dose.</p>'
    who = f' for {esc(F["name"])}' if F['name'] else ''
    extra = '''.ck td:first-child.box{width:28px;font-size:18px;color:var(--mut)}.ck td{font-size:14.5px}h2{margin-top:36px}
.printbtn{float:right;font:inherit;font-size:14px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
@media (max-width:640px){.ck thead{display:none}.ck tr{display:block;border-bottom:1px solid var(--line);padding:8px 0}.ck td{display:block;border:0;padding:2px 0}
 .ck td[data-l]::before{content:attr(data-l) ": ";font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em}.ck td.box{display:none}}
@media print{:root{--bg:#fff;--fg:#000;--mut:#444;--card:#fff;--line:#bbb;--acc:#000}body{font-size:12px}main{padding:0;max-width:none}
 .printbtn,footer,p.crumbs{display:none}h2,h2+p{break-after:avoid}h1{font-size:22px}h2{font-size:16px;margin:18px 0 4px}tr{break-inside:avoid}.panel{border:0;padding:0}.ck td{font-size:12px;padding:4px 6px}}'''
    body = f'''<main><p class="crumbs"><a href="index.html">← All reports</a></p>
<button class="printbtn" onclick="window.print()">Print</button>
<div class="kicker">For your doctor · {today}</div>
<h1>Check-ups and medicine notes{who}</h1>
<p class="lede">A short list to bring to a check-up. It comes from a private analysis of a consumer DNA test ({esc(FORMAT.get(F["sample"]["format"], F["sample"]["format"]))} raw data). None of it is a diagnosis; it shows which routine tests are most worth doing and which medicines need a second look.</p>
{NOTICE}
<div class="callout"><b>Please note</b><ul><li>These results come from a consumer DNA chip, not a clinical test. Before acting on a medicine result, a clinical test can confirm it.</li>
<li>{"No disease-causing variant was found; the items below are common genetic tendencies that shift chances slightly." if not F["clinvar"] else "A few rare variants need clinical confirmation before anyone acts on them (see the main report)."}</li></ul></div>
{secs}
<footer><a href="index.html">← All reports</a> · Made privately on this computer.</footer></main>'''
    (ctx.out / 'Doctor_Checklist.html').write_text(page('Doctor Checklist', body, extra))


def ancestry_page(ctx, F):
    w = ctx.work
    blocks = []
    y, mt = F['y'], F['mt']
    lines = ''
    if y.get('haplogroup'):
        lines += (f'<div class="card"><b>Father-line (Y chromosome)</b><div class="big">{esc(y["haplogroup"])}</div><small>{esc(y.get("haplogroup_long", ""))}</small>'
                  f'<p>{esc(describe(y.get("haplogroup_long") or y["haplogroup"], YDESC))}</p></div>')
    elif F['sample']['sex'] == 'female':
        lines += '<div class="card"><b>Father-line (Y chromosome)</b><p>Only men carry a Y chromosome. A father, brother or paternal uncle could test to find it.</p></div>'
    if mt.get('haplogroup'):
        q = mt.get('quality', 0)
        lines += (f'<div class="card"><b>Mother-line (mitochondrial DNA)</b><div class="big">{esc(mt["haplogroup"])}</div>'
                  f'<small>match quality {q:.2f}{" (the main branch is certain; the last letters less so)" if q < 0.8 else ""}</small>'
                  f'<p>{esc(describe(mt["haplogroup"], MTDESC))}</p></div>')
    blocks.append(f'<h2 id="lines">Father-line and mother-line</h2><p class="mut">These follow just one ancestor in each generation: your father\'s father\'s father… and your mother\'s mother\'s mother…</p><div class="two">{lines}</div>')

    if F['aadr']:
        a = F['aadr']
        mods = list(a['closest_modern'].items())[:12]
        mx = max(v for _, v in mods)
        rows = ''.join(f'<div class="mrow"><span class="mname">{esc(k.replace("_", " "))}</span><span class="mtrack"><span class="mbar acc" style="width:{(1 - v / (mx * 1.15)) * 100:.0f}%"></span></span><span class="mp">{i + 1}</span></div>' for i, (k, v) in enumerate(mods))
        mix = ''
        for key, title, note in (('mixture_modern', 'As a mix of present-day populations', 'A rough fit of you as a mix of today\'s groups.'),
                                 ('mixture_historic', 'As a mix of historic-era populations', 'Ancient genomes from the last ~2,500 years.'),
                                 ('mixture_deep', 'Deep-time ancestry', 'The ancient groups most Europeans and West Asians descend from.')):
            m = a.get(key)
            if not m: continue
            segs = ''.join(f'<div class="seg{" sm" if v < .15 else ""}" style="flex:{v:.4f};background:var(--s{i % 8 + 1})" data-tip="{esc(k.replace("_", " "))}: {v * 100:.0f}%" tabindex="0"><span>{v * 100:.0f}%</span></div>' for i, (k, v) in enumerate(m.items()))
            leg = ''.join(f'<span><i style="background:var(--s{i % 8 + 1})"></i>{esc(k.replace("_", " "))}</span>' for i, (k, v) in enumerate(m.items()))
            mix += f'<h3>{title}</h3><p class="mut small">{note}</p><div class="legend">{leg}</div><div class="bar">{segs}</div>'
        q = a.get('qpadm_best')
        qhtml = ''
        if q:
            qhtml = (f'<h3>Formal test (qpAdm)</h3><p>The best-supported model of the ones tested: ' + ', '.join(f'<b>{esc(k)}</b> {v * 100:.0f}%' for k, v in q['weights'].items()) +
                     f' (fit p = {q["p"]:.2f}; above 0.05 means the model fits). Several models often fit; this one fits best.</p>')
        pcs = ''.join(f'<img class="plot" src="{img64(w / "ancient" / f)}" alt="PCA plot" style="margin:10px 0">' for f in ('pca_world.png', 'pca_west.png', 'pca_ancient.png') if (w / 'ancient' / f).exists())
        blocks.append(f'''<h2 id="ancient">Where your ancestors came from</h2>
<p>Compared with about 4,500 present-day people from 260 populations worldwide (Allen Ancient DNA Resource), these groups are genetically closest to you:</p>
<div class="panel">{rows}</div>{mix}{qhtml}
<details><summary>Maps of genetic similarity (PCA)</summary><p class="mut small">Each dot is a person; closeness means genetic similarity. The star is you.</p>{pcs}</details>
<p class="mut small">These are best-fitting models, not a family tree; different reference groups can fit almost equally well.</p>''')
    if F['anc']:
        an = F['anc']
        img = f'<img class="plot" src="{img64(w / "pgs" / "pca.png")}" alt="PCA">' if (w / 'pgs' / 'pca.png').exists() else ''
        near = ''.join(f'<li>{esc(n)}</li>' for n in an['nearest_names'][:6])
        verdict = ('You sit within the normal spread of the closest population.' if an.get('close_match', True) else
                   'You are not a close match to any of these populations; you sit between the groups this reference has. '
                   'That is expected for people with roots in the Middle East, the Caucasus, North Africa or Central Asia, which 1000 Genomes does not cover, '
                   'and for people of mixed ancestry.')
        blocks.append(f'''<h2 id="kg">Your place among the 1000 Genomes populations</h2>
<p>This reference (2,504 people from 26 populations) is used to compare your polygenic scores with people of similar ancestry. The populations closest to you, nearest first:</p>
<div class="panel"><ol class="near">{near}</ol></div><p>{verdict}</p>{img}''')
    roh = F['sample'].get('roh')
    if roh:
        blocks.append(f'''<h2 id="roh">Were your parents related?</h2><p>{
            {"none": "No sign of it.", "distant": "Possibly distantly.", "close": "Probably yes."}[roh["verdict"]]} Children of related parents have long DNA stretches that are identical on both copies.
You have {roh["n"]} such stretches longer than 1 Mb, {roh["total_mb"]:.0f} Mb in total, the longest {roh["longest_mb"]:.1f} Mb. Children of first cousins typically have over 150 Mb with stretches of 20 Mb or more.</p>''')
    if not F['aadr'] and not F['anc']:
        blocks.append('<p class="callout">For an ancestry estimate, run the kit again and choose “Ancient-DNA ancestry” (and optionally imputation). Everything done so far is kept.</p>')
    body = f'''<main><p class="crumbs"><a href="index.html">← All reports</a></p>
<div class="kicker">Ancestry · local only</div><h1>Ancestry and family lines</h1>
<p class="lede">Where your DNA fits among people living today and in the past. Nothing on this page is about health.</p>
{"".join(blocks)}
<footer><a href="index.html">← All reports</a> · Made privately on this computer.</footer></main>'''
    (ctx.out / 'Ancestry.html').write_text(page('Ancestry', body))


def effects_page(ctx, F):
    e = F['eff']
    rows = ''.join(f'<tr><td><b>{esc(r["gene"])}</b> {esc(r["protein_change"])}</td><td>{esc(r["copies_text"])}</td><td class=num>{r["am"]:.2f}</td><td class=num>{r["revel"] if r["revel"] is not None else "–"}</td><td>{esc(r["note"])}</td></tr>' for r in e['notable'])
    body = f'''<main><p class="crumbs"><a href="index.html">← All reports</a></p>
<div class="kicker">Variant effects · local only</div><h1>Small changes in your genes</h1>
<p class="lede">Your DNA carries {e["n_missense"]:,} protein-changing variants (each changes one building block of a protein). Two prediction tools, AlphaMissense and REVEL, estimate which of them might damage the protein.</p>
{NOTICE}
<div class="callout">{esc(e["summary"])}</div>
<h2>Variants predicted damaging in genes with known disease links</h2>
<p class="mut">Predictions are not diagnoses: most people carry a handful of “damaging-looking” variants without any effect, and rare chip calls are often wrong.</p>
<div class="panel tw"><table><thead><tr><th>Gene and change</th><th>Copies</th><th class=num>AlphaMissense</th><th class=num>REVEL</th><th>Note</th></tr></thead><tbody>{rows or "<tr><td colspan=5>None.</td></tr>"}</tbody></table></div>
<p class="mut small">AlphaMissense above 0.56 and REVEL above 0.5 suggest a damaging change. “Measured” means the chip read the position; “estimated” means imputed.</p>
<footer><a href="index.html">← All reports</a> · Made privately on this computer.</footer></main>'''
    (ctx.out / 'Variant_Effects.html').write_text(page('Variant Effects', body))


def index_page(ctx, F):
    pages = [('Genome_Report.html', 'Genome Report', 'Start here. Medicines, health findings, polygenic scores, traits and next steps, in plain words.'),
             ('Doctor_Checklist.html', 'Doctor checklist', 'Printable list of check-up tests and the medicine card.'),
             ('Ancestry.html', 'Ancestry and family lines', 'Father-line, mother-line and where your ancestors came from.')]
    if F['eff']: pages.append(('Variant_Effects.html', 'Small changes in your genes', 'Predicted effects of the protein-changing variants you carry.'))
    cards = ''.join(f'<a class="pcard" href="{f}"><b>{esc(t)} ↗</b><span>{esc(d)}</span></a>' for f, t, d in pages)
    from .. import __main__ as M
    steps = ''.join(f'<li><b>{esc(desc)}</b> <span class="mut">{esc(F["status"].get(sid, {}).get("state", "not run"))}{(": " + esc(F["status"][sid]["msg"])) if F["status"].get(sid, {}).get("msg") else ""}</span></li>'
                    for sid, tier, fn, desc, _ in M.steps() if sid != 'report')
    who = f'{esc(F["name"])}\'s' if F['name'] else 'Your'
    body = f'''<main><div class="kicker">genome-kit · local only · {datetime.date.today().isoformat()}</div>
<h1>{who} genome, all in one place</h1>
<p class="lede">Every report built from {"your" if not F["name"] else "this"} raw DNA file. Everything here was computed on this computer; nothing derived from the genome has been uploaded.</p>
{NOTICE}
<div class="pages">{cards}</div>
<details><summary>For the curious: how this was made</summary><ul class="small">{steps}</ul>
<p class="mut small">Source file: {esc(F["sample"]["source_file"])} ({esc(FORMAT.get(F["sample"]["format"], F["sample"]["format"]))}, {F["sample"]["markers"]:,} markers, {F["sample"]["call_rate"] * 100:.1f}% called, genetic sex {esc(F["sample"]["sex"])}).</p></details>
<footer>Made privately on this computer with genome-kit. Keep these files private; they describe your health.</footer></main>'''
    (ctx.out / 'index.html').write_text(page('Genome Hub', body))


def build(ctx):
    F = collect(ctx)
    jdump({k: v for k, v in F.items() if k not in ('status',)}, ctx.work / 'facts.json')
    main_report(ctx, F); checklist(ctx, F); ancestry_page(ctx, F); index_page(ctx, F)
    if F['eff']: effects_page(ctx, F)
    return f'{4 + bool(F["eff"])} pages'
