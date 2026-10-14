# Evaluate the curated marker knowledge base for one person -> work/markers.json
# Output: {'items': [...report items...], 'fine': [...lines...], 'traits': [...], 'calls': {id: count}, 'check': [...]}
from ..genotypes import Genome
from ..kb.markers import MARKERS, SCREEN
from ..util import jdump, jload


def run(ctx):
    sample = jload(ctx.work / 'sample.json')
    imp = ctx.work / 'imputed' if (ctx.work / 'imputed' / 'me.chr22.vcf.gz').exists() else None
    G = Genome(ctx.genome, imp, sample['sex'])
    hla = jload(ctx.work / 'hla.json', {})
    calls = {m['id']: G.count(m) for m in MARKERS}
    M = {m['id']: m for m in MARKERS}
    items, fine, traits, check, unread = [], [], [], [], []
    n = lambda k: calls[k]['n'] if calls.get(k) else None

    def add(item, section='health', source_ids=()):
        src = [calls[i] for i in source_ids if calls.get(i)]
        if any(s['source'] == 'imputed' for s in src):
            item = dict(item); item['note'] = (item.get('note', '') + ' Estimated from imputation (not measured directly by the chip); a clinical test can confirm it.').strip()
        (traits if section == 'traits' else items).append(item)

    for m in MARKERS:
        if m.get('handler'): continue
        c = calls[m['id']]
        if c is None:
            if m['id'] in SCREEN: unread.append(m['name'])
            continue
        if not c['certain']: continue
        t = m.get('texts', {}).get(c['n'])
        if t: add(t, m.get('section', 'health'), [m['id']])
        elif c['n'] == 0 and m.get('fine'): fine.append(m['fine'])
        for row in m.get('check', {}).get(c['n'], []): check.append(dict(zip(('test', 'why', 'when'), row)))

    # ---- APOE
    e4, e2 = n('apoe_112'), n('apoe_158')
    if e4 is not None and e2 is not None:
        geno = {(0, 0): 'ε3/ε3', (1, 0): 'ε3/ε4', (2, 0): 'ε4/ε4', (0, 1): 'ε2/ε3', (0, 2): 'ε2/ε2', (1, 1): 'ε2/ε4'}.get((e4, e2), 'unclear')
        if e4 == 0:
            fine.append(f'APOE {geno}: {"the most common type, average" if e2 == 0 else "slightly lower than average"} Alzheimer\'s risk')
        else:
            add(dict(level='know', title=f'Alzheimer\'s disease and cholesterol: APOE {geno}',
                     finding=f'You carry {"one copy" if e4 == 1 else "two copies"} of <b>APOE ε4</b>, the strongest common gene factor for late-onset Alzheimer\'s disease. About 1 in 4 people carry one copy; about 1 in 50 carry two.',
                     what='APOE also affects cholesterol. ε4 tends to raise LDL a little.',
                     size=('With one ε4 copy, the chance of Alzheimer\'s by age 85 is roughly 1 in 4 to 1 in 3 for men and somewhat higher for women, against about 1 in 10 for ε3/ε3. Many carriers never develop it.'
                           if e4 == 1 else 'With two copies, the chance of Alzheimer\'s by age 85 is roughly 1 in 2. It is not a certainty, and the age of onset varies a lot.'),
                     todo='No test or treatment is recommended because of APOE alone. What helps brain health in general also helps here: blood pressure, exercise, sleep, hearing aids if needed, not smoking. Consider genetic counselling before sharing this result with relatives.'),
                source_ids=['apoe_112', 'apoe_158'])

    # ---- HFE (haemochromatosis)
    c282, h63 = n('hfe_c282y'), n('hfe_h63d')
    if c282 is not None:
        if c282 == 2:
            add(dict(level='act', title='Iron overload (haemochromatosis): two C282Y copies',
                     finding='You carry <b>two copies of HFE C282Y</b>, the genotype behind most hereditary haemochromatosis.',
                     size='Many people with this genotype absorb too much iron over the years. About 1 in 4 men develop iron-related problems (liver, joints, diabetes); women are protected until menopause. It is easy to prevent by giving blood regularly.',
                     todo='Ask for a ferritin and transferrin-saturation blood test. If iron is high, regular blood removal treats it completely.'), source_ids=['hfe_c282y'])
            check.append(dict(test='Ferritin and transferrin saturation', why='Two HFE C282Y copies (haemochromatosis genotype)', when='Now, then as advised'))
        elif c282 == 1 and h63:
            add(dict(level='know', title='Iron: HFE C282Y + H63D (compound)', finding='One copy each of HFE C282Y and H63D.',
                     size='Only a small minority with this combination ever store too much iron (about 1 in 100).',
                     todo='A ferritin test at a routine check-up is a sensible one-off.'), source_ids=['hfe_c282y', 'hfe_h63d'])
            check.append(dict(test='Ferritin', why='HFE C282Y + H63D', when='Once'))
        elif c282 == 1:
            fine.append('Haemochromatosis: one C282Y copy (carrier only; carriers do not develop iron overload)')
        elif h63 == 2:
            fine.append('Haemochromatosis: two H63D copies (C282Y absent); iron overload is very rare with this')
        elif h63 == 1:
            fine.append('Haemochromatosis: only one harmless H63D copy (C282Y absent)')
        else:
            fine.append('Haemochromatosis (HFE C282Y, H63D): not present')

    # ---- alpha-1 antitrypsin
    z, s = n('serpina1_z'), n('serpina1_s')
    if z is not None or s is not None:
        z, s = z or 0, s or 0
        if z == 2 or (z == 1 and s >= 1):
            add(dict(level='act', title=f'Lungs and liver: alpha-1 antitrypsin {"ZZ" if z == 2 else "SZ"}',
                     finding=f'You carry the alpha-1 antitrypsin <b>{"ZZ" if z == 2 else "SZ"}</b> genotype, which lowers a protein that protects the lungs.',
                     size='People with this genotype have a much higher chance of emphysema (especially if they smoke) and, for ZZ, liver disease.',
                     todo='Never smoke. Ask a doctor for an alpha-1 antitrypsin blood level test and lung function check.'), source_ids=['serpina1_z', 'serpina1_s'])
            check.append(dict(test='Alpha-1 antitrypsin level, lung function', why='SERPINA1 Z/S genotype', when='Once'))
        elif z == 1 or s >= 1:
            add(dict(level='ok', title='Alpha-1 antitrypsin: carrier', finding=f'One copy of the alpha-1 antitrypsin <b>{"Z" if z else "S"}</b> variant (carrier).',
                     size='Carriers are usually healthy; smoking is a bit more harmful to the lungs than for non-carriers.', todo='Not smoking is the main advice. Relevant for family planning.'),
                source_ids=['serpina1_z', 'serpina1_s'])
        else:
            fine.append('Alpha-1 antitrypsin Z and S: not present')

    # ---- Familial Mediterranean Fever
    mefv = [M[i]['name'].replace('MEFV ', '') for i in ('mefv_m694v', 'mefv_m680i', 'mefv_v726a', 'mefv_a744s') if n(i)]
    mefv_tot = sum(n(i) or 0 for i in ('mefv_m694v', 'mefv_m680i', 'mefv_v726a', 'mefv_a744s'))
    if any(calls[i] for i in ('mefv_m694v', 'mefv_m680i', 'mefv_v726a')):
        if mefv_tot >= 2:
            add(dict(level='act', title='Familial Mediterranean Fever (FMF): two variants', finding=f'Two MEFV variants were called ({", ".join(mefv)}).',
                     what='FMF causes repeated attacks of fever with belly, chest or joint pain. It is common in Turkey, Armenia, among Sephardic Jews and in the Arab world.',
                     todo='If you ever had such attacks, see a doctor: colchicine treats FMF very well. A clinical genetic test confirms the result.'), source_ids=['mefv_m694v', 'mefv_m680i', 'mefv_v726a', 'mefv_a744s'])
        elif mefv_tot == 1:
            add(dict(level='ok', title='Familial Mediterranean Fever: carrier', finding=f'One MEFV variant ({mefv[0]}): you are a carrier.',
                     size='Carriers usually have no symptoms (about 1 in 5 people in Turkey carry one). If a partner is also a carrier, a child can have FMF.',
                     todo='Relevant for family planning. Rare chip calls can be wrong, so confirm before relying on it.'))
        else:
            fine.append('Familial Mediterranean Fever (MEFV M694V, M680I, V726A, A744S): not present')

    # ---- G6PD (X-linked)
    g6 = [i for i in ('g6pd_med', 'g6pd_a', 'g6pd_canton') if n(i)]
    if any(calls[i] for i in ('g6pd_med', 'g6pd_a', 'g6pd_canton')):
        if g6:
            male = sample['sex'] == 'male'
            hom = any(n(i) == 2 for i in g6)
            deficient = male or hom
            add(dict(level='act' if deficient else 'know', title='G6PD deficiency (favism)' + ('' if deficient else ': carrier'),
                     finding=f'You carry the <b>{M[g6[0]]["name"]}</b> variant{" on your only X chromosome" if male else (" on both X chromosomes" if hom else " on one X chromosome")}.',
                     what='G6PD protects red blood cells. When it is low, fava beans and some medicines (for example primaquine, dapsone, rasburicase, high-dose aspirin, some sulfa antibiotics) can break red cells down.',
                     todo=('Avoid fava beans and tell every doctor and pharmacist. A G6PD enzyme blood test confirms it.' if deficient else
                           'Women carriers are usually fine but can have lowered G6PD. A G6PD blood test answers it; mention it if one of these medicines is suggested.')),
                source_ids=g6)
            if deficient: check.append(dict(test='G6PD enzyme test', why=M[g6[0]]['name'] + ' variant', when='Once'))
        else:
            fine.append('G6PD deficiency (favism) variants: none')

    # ---- MTHFR
    a, b = n('mthfr677'), n('mthfr1298')
    if a is not None:
        if a == 2:
            add(dict(level='ok', title='MTHFR C677T: two copies', finding='Two copies of MTHFR C677T, like about 1 in 10 people.',
                     size='This can raise homocysteine a little when folate intake is low. Major medical guidelines advise against testing or treating it.',
                     todo='Nothing special: a normal diet with vegetables (or the usual folic acid in pregnancy) is enough.'), source_ids=['mthfr677'])
        else:
            fine.append('MTHFR: normal' if a == 0 and not b else 'MTHFR: common variant forms only, no practical effect')

    # ---- Lp(a)
    l1, l2 = n('lpa'), n('lpa2')
    if (l1 or 0) + (l2 or 0) >= 1:
        add(dict(level='know', title='Lp(a) cholesterol: raising variant', finding='You carry a common LPA variant that raises <b>lipoprotein(a)</b>, a cholesterol type set mainly by genes.',
                 size='About 1 in 5 people have high Lp(a); it raises heart-attack risk on its own and diet barely changes it. The chip only reads part of the LPA gene, so a blood test is the real answer.',
                 todo='Ask for a one-time Lp(a) blood test.'), source_ids=['lpa', 'lpa2'])
        check.append(dict(test='Lipoprotein(a), Lp(a)', why='LPA variant that raises Lp(a)', when='Once in a lifetime'))

    # ---- alcohol
    al, ad = n('aldh2'), n('adh1b')
    if al is not None or ad is not None:
        if al:
            add(dict(level='know', title='Alcohol: flush variant (ALDH2)', finding=f'{"One copy" if al == 1 else "Two copies"} of the ALDH2*2 “Asian flush” variant.',
                     what='Alcohol turns into acetaldehyde, which your body clears slowly: face reddening, fast heartbeat, nausea.',
                     size='People with the flush variant who drink regularly have a much higher risk of oesophageal cancer (several-fold for one copy).',
                     todo='The safest choice is to drink little or no alcohol.'), source_ids=['aldh2'])
        txt = 'No alcohol-flush variant.' if not al else ''
        if ad: txt += f' {"One" if ad == 1 else "Two"} “fast” alcohol-processing cop{"y" if ad == 1 else "ies"} (ADH1B), linked to drinking a little less.'
        if txt.strip(): traits.append(dict(level='fun', title='Alcohol', finding=txt.strip()))

    # ---- skin
    s1, s2 = n('slc24a5'), n('slc45a2')
    if s1 is not None and s2 is not None:
        if s1 == 2 and s2 == 2: t = 'Both main “lighter skin” gene versions are present in two copies, typical of Europe and West Asia. Light skin burns more easily, so sun protection matters.'
        elif s1 + s2 == 0: t = 'Neither of the two main European/West-Asian “lighter skin” gene versions is present.'
        else: t = f'A mix of the main “lighter skin” gene versions ({s1 + s2} of 4 copies).'
        traits.append(dict(level='fun', title='Skin', finding=t))

    # ---- ABO blood group
    bo, oo = n('abo_b'), n('abo_o')
    if bo is not None and oo is not None and calls['abo_o']['source'] == 'chip':
        a_ = 2 - bo - oo
        if a_ >= 0:
            al_ = ['A'] * a_ + ['B'] * bo + ['O'] * oo
            grp = 'AB' if (a_ and bo) else 'A' if a_ else 'B' if bo else 'O'
            traits.append(dict(level='fun', title='Blood group', finding=f'<b>{grp}</b> ({"/".join(al_)}). Rh (positive/negative) cannot be read from this chip.'))

    # ---- celiac / DQ2.5 (HLA typing preferred)
    dq = n('dq25')
    if hla.get('DQB1') and hla.get('DQA1'):
        pass  # handled from HLA typing in facts.py
    elif dq:
        add(dict(level='know', title='Autoimmune tendency: HLA-DQ2.5 marker',
                 finding=f'You carry {"one copy" if dq == 1 else "two copies"} of a marker for <b>HLA-DQ2.5</b>, the main gene type that allows celiac disease (and is linked to type 1 diabetes and thyroid autoimmunity).',
                 size='About 1 in 3 people carry DQ2.5 or DQ8, and only about 1 in 30 of them ever develop celiac disease.',
                 todo='Nothing now. Lasting digestive trouble, anaemia or unexplained tiredness would be a reason for a celiac blood test (tTG-IgA) while still eating gluten.'), source_ids=['dq25'])
        check.append(dict(test='Celiac antibodies (tTG-IgA)', why='HLA-DQ2.5 marker', when='Only if symptoms appear', conditional=True))

    out = dict(items=items, fine=fine, traits=traits, check=check, unread=unread,
               calls={k: v for k, v in calls.items() if v}, proxies={k: n(k) for k in ('a3101', 'b5701', 'dq25')})
    jdump(out, ctx.work / 'markers.json')
    return f'{sum(1 for v in calls.values() if v)} of {len(MARKERS)} markers read'
