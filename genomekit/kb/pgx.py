# Plain-language medicine-gene interpretations keyed on PharmCAT phenotypes (CPIC/DPWG guideline content,
# rewritten for ordinary readers). Each rule returns a report item plus a "medicine card" row for the doctor checklist.
# Wording follows CPIC guidelines as of 2025; numbers are rounded, published figures.

def _item(level, title, finding, what, size, todo, card, note=''):
    return dict(level=level, title=title, finding=finding, what=what, size=size, todo=todo, note=note), card


def interpret(P, hla, proxies, sex):
    """P: {gene: dict(phenotype=str, diplotype=str, uncertain=bool)} from PharmCAT.
    hla: HLA typing (or {}); proxies: tag-SNP copy counts used when HLA typing was not run.
    Returns (items, cards, normal_genes)."""
    items, cards, normal = [], [], []
    ph = lambda g: (P.get(g) or {}).get('phenotype', '') or ''
    dip = lambda g: (P.get(g) or {}).get('diplotype', '') or ''

    def add(t):
        items.append(t[0]); cards.append(t[1])

    # ---------------- HLA-A*31:01 / HLA-B*15:02: carbamazepine, oxcarbazepine, phenytoin
    a3101 = hla_has(hla, 'A', '31:01')
    src = 'HLA typing'
    if a3101 is None and proxies.get('a3101') is not None:
        a3101 = proxies['a3101'] > 0; src = 'a marker SNP that usually travels with it (tag rs1061235)'
    if a3101:
        add(_item('act', 'Carbamazepine (and oxcarbazepine)',
                  f'You carry the immune-system gene type <b>HLA-A*31:01</b> (found by {src}).',
                  'Carbamazepine is used for epilepsy, nerve pain and sometimes mood disorders. In people with HLA-A*31:01 it more often causes a serious allergic-type skin reaction.',
                  'In a large European study, about 1 in 4 carriers who took carbamazepine had an allergic-type reaction (mostly a rash), against about 1 in 17 non-carriers. Severe, dangerous reactions are much rarer, but they are the reason for the warning.',
                  'If carbamazepine or oxcarbazepine is ever suggested, mention this result. Guidelines advise choosing a different medicine. A clinical HLA test can confirm it first.',
                  ['<b>Carbamazepine, oxcarbazepine</b>', '<b>Choose a different medicine</b> (higher risk of a serious allergic-type skin reaction)', 'HLA-A*31:01 carrier'],
                  note='' if src == 'HLA typing' else 'This comes from a tag marker, which can be wrong outside European ancestry; a clinical HLA test settles it.'))
    if hla_has(hla, 'B', '15:02'):
        add(_item('act', 'Carbamazepine, oxcarbazepine and phenytoin (HLA-B*15:02)',
                  'You carry <b>HLA-B*15:02</b>, common in South-East and East Asia.',
                  'These anti-seizure medicines can cause Stevens–Johnson syndrome, a dangerous skin reaction, in carriers.',
                  'In carriers the risk of this reaction to carbamazepine is up to about 1 in 20; without B*15:02 it is under 1 in 1,000.',
                  'Guidelines say: do not start carbamazepine or oxcarbazepine, and avoid phenytoin/fosphenytoin. Mention this before any anti-seizure medicine.',
                  ['<b>Carbamazepine, oxcarbazepine, phenytoin</b>', '<b>Avoid</b> (risk of Stevens–Johnson syndrome)', 'HLA-B*15:02 carrier']))
    b5701 = hla_has(hla, 'B', '57:01')
    bsrc = 'HLA typing'
    if b5701 is None and proxies.get('b5701') is not None:
        b5701 = proxies['b5701'] > 0; bsrc = 'a tag marker (rs2395029)'
    if b5701:
        add(_item('act', 'Abacavir (HIV medicine)', f'You carry <b>HLA-B*57:01</b> (found by {bsrc}).',
                  'Abacavir is used to treat HIV. Carriers of HLA-B*57:01 often get a serious hypersensitivity reaction to it.',
                  'About half of carriers react to abacavir; non-carriers almost never do.',
                  'Abacavir should not be used. This is already standard: clinics test for B*57:01 before prescribing it.',
                  ['<b>Abacavir</b>', '<b>Do not use</b>', 'HLA-B*57:01 carrier'],
                  note='' if bsrc == 'HLA typing' else 'From a tag marker; the standard clinical HLA-B*57:01 test settles it.'))
    if hla_has(hla, 'B', '58:01'):
        add(_item('act', 'Allopurinol (gout medicine)', 'You carry <b>HLA-B*58:01</b>.',
                  'Allopurinol lowers uric acid in gout. Carriers have a much higher risk of a severe skin reaction (SJS/TEN or DRESS).',
                  'The reaction is still rare in carriers (roughly 1 in 50–100), but it can be life-threatening.',
                  'Guidelines advise another uric-acid medicine (for example febuxostat) instead of allopurinol.',
                  ['<b>Allopurinol</b>', 'Choose another uric-acid medicine', 'HLA-B*58:01 carrier']))

    # ---------------- warfarin: VKORC1 + CYP2C9 (+ CYP4F2)
    vk = dip('VKORC1').count('variant (T)')
    c9 = ph('CYP2C9')
    if 'VKORC1' in P:
        c9_slow = 'Intermediate' in c9 or 'Poor' in c9
        if vk == 2 or (vk == 1 and c9_slow) or 'Poor' in c9:
            very = (vk == 2 and c9_slow) or 'Poor' in c9
            dose = '0.5–2 mg' if very else ('about 2–3 mg' if vk == 2 else 'about 3 mg')
            genes = ', '.join(x for x in [f'VKORC1 −1639 {"TT" if vk == 2 else "CT" if vk == 1 else "CC"}', f'CYP2C9 {dip("CYP2C9").split(" OR ")[0]}' if c9_slow or 'Poor' in c9 else '',
                                          'CYP4F2 *3 (one copy)' if '*3' in dip('CYP4F2') else ''] if x)
            add(_item('act', 'Warfarin (blood thinner)',
                      f'Your genes (<b>{genes}</b>) make you <b>{"very " if very else ""}sensitive</b> to warfarin.',
                      'Warfarin prevents blood clots and its dose must be just right. Too much causes bleeding.',
                      f'People with your combination usually need a lower dose, roughly {dose} a day instead of the typical 5 mg.',
                      'If warfarin is ever needed, tell the doctor. They have dose calculators that use these genes. Newer blood thinners (apixaban, rivaroxaban and similar) are not affected.',
                      ['<b>Warfarin</b>', f'Lower dose (roughly {dose}/day); use a genotype dosing calculator. Newer blood thinners are not affected.', genes]))
        else:
            normal.append('warfarin genes (VKORC1, CYP2C9)')

    # ---------------- statins: SLCO1B1 (+ ABCG2 for rosuvastatin)
    s1 = ph('SLCO1B1')
    if 'Poor' in s1 or 'Decreased' in s1:
        poor = 'Poor' in s1
        add(_item('act', 'Statins (cholesterol medicines)', f'Your <b>SLCO1B1</b> gene has <b>{"poor" if poor else "decreased"} function</b>.',
                  'SLCO1B1 moves statins into the liver. When it is slow, more statin stays in the blood and muscles.',
                  ('With high-dose simvastatin (80 mg), a large trial found muscle damage over 5 years in about 3 in 100 people with one slow copy, versus about 1 in 200 for most people; with two slow copies it was about 1 in 6. Other statins are much less affected.'),
                  'If a statin is ever needed, mention this. Guidelines suggest a different statin (for example rosuvastatin or pravastatin) or a low dose rather than simvastatin.',
                  ['Statins', 'Avoid high-dose simvastatin; prefer rosuvastatin or pravastatin, or a low dose', f'SLCO1B1 {"poor" if poor else "decreased"} function']))
    elif s1: normal.append('SLCO1B1 (statins)')
    ab = ph('ABCG2')
    if 'Poor' in ab or 'Decreased' in ab:
        add(_item('act', 'Rosuvastatin', '<b>ABCG2</b> has reduced function (Q141K variant).',
                  'ABCG2 clears rosuvastatin. Slower clearance means higher levels.', 'Guidelines suggest starting rosuvastatin at 20 mg/day or less.',
                  'Mention it if rosuvastatin is prescribed.', ['Rosuvastatin', 'Start at 20 mg/day or less', 'ABCG2 reduced function']))

    # ---------------- CYP2C9 alone: NSAIDs, phenytoin
    if 'Intermediate' in c9 or 'Poor' in c9:
        poor = 'Poor' in c9
        add(_item('act', 'Painkillers (NSAIDs) and phenytoin', f'<b>CYP2C9 {dip("CYP2C9").split(" OR ")[0]}</b>: you break these down more slowly ({"poor" if poor else "intermediate"} metaboliser).',
                  'NSAIDs are common painkillers such as ibuprofen, celecoxib and meloxicam. Phenytoin is an epilepsy drug.',
                  ('Slower breakdown means higher drug levels and more side effects (stomach, kidneys). ' +
                   ('Guidelines say: celecoxib/ibuprofen start at 25–50% of the lowest dose; avoid meloxicam and piroxicam; phenytoin about 50% lower dose.' if poor else
                    'Guidelines say: celecoxib or ibuprofen, start at the lowest dose; <b>meloxicam</b>, start at half the lowest dose; <b>piroxicam</b>, choose another drug; phenytoin, about 25% lower dose.')),
                  'For occasional ibuprofen, simply use the lowest effective dose. Mention it if a doctor prescribes NSAIDs long-term or phenytoin.',
                  ['NSAIDs (long-term), phenytoin', 'Celecoxib/ibuprofen: lowest dose; meloxicam: half the lowest dose; piroxicam: avoid; phenytoin: about 25% lower dose' if not poor else
                   'Celecoxib/ibuprofen: 25–50% of lowest dose; avoid meloxicam and piroxicam; phenytoin: about 50% lower dose', f'CYP2C9 {dip("CYP2C9").split(" OR ")[0]}']))
    elif c9: normal.append('CYP2C9 (painkillers)')

    # ---------------- CYP2C19
    c19 = ph('CYP2C19')
    d19 = dip('CYP2C19').split(' OR ')[0]
    if 'Poor' in c19 or 'Intermediate' in c19:
        poor = 'Poor' in c19
        add(_item('act', 'Clopidogrel (heart stents) and some other medicines', f'<b>CYP2C19 {d19}</b>: {"poor" if poor else "intermediate"} metaboliser.',
                  'Clopidogrel needs CYP2C19 to become active. It is given after heart stents and some strokes.',
                  ('Clopidogrel works much less well for you: guidelines advise prasugrel or ticagrelor instead.' if poor else
                   'Clopidogrel works less well; after a stent, guidelines advise prasugrel or ticagrelor instead.') +
                  ' Omeprazole-type stomach drugs stay in the body longer (usually fine, even helpful).' +
                  (' Citalopram, escitalopram and sertraline: guidelines suggest a 50% lower starting dose.' if poor else ''),
                  'Mention this if clopidogrel is ever considered (for example after a stent).',
                  ['<b>Clopidogrel</b>', 'Prefer prasugrel or ticagrelor', f'CYP2C19 {d19} ({"poor" if poor else "intermediate"} metaboliser)']))
    elif 'Rapid' in c19 or 'Ultrarapid' in c19:
        ultra = 'Ultrarapid' in c19
        add(_item('act', 'Voriconazole (antifungal) and some stomach-acid drugs', f'<b>CYP2C19 {d19}</b>: you are {"an <b>ultrarapid" if ultra else "a <b>rapid"} metaboliser</b>.',
                  'CYP2C19 breaks down voriconazole, proton-pump inhibitors (omeprazole and similar) and some antidepressants.',
                  'Voriconazole may clear too fast to work, so guidelines advise a different antifungal. Omeprazole-type drugs may need a higher dose for some uses (for example H. pylori treatment). '
                  + ('Citalopram/escitalopram may not work well; guidelines suggest another antidepressant. ' if ultra else '') + 'Clopidogrel works normally.',
                  'Only relevant if one of these is prescribed. Mention it then.',
                  ['Voriconazole; omeprazole-type drugs', 'Voriconazole: consider another antifungal. Omeprazole-type: may need a higher dose (e.g. H. pylori treatment)', f'CYP2C19 {d19} ({"ultra" if ultra else ""}rapid metaboliser)']))
    elif c19: normal.append('CYP2C19 (clopidogrel, antidepressants)')

    # ---------------- thiopurines: TPMT / NUDT15
    for g in ('TPMT', 'NUDT15'):
        p = ph(g)
        if 'Poor' in p or 'Intermediate' in p:
            poor = 'Poor' in p
            add(_item('act', f'Thiopurines: azathioprine, mercaptopurine ({g})', f'<b>{g} {dip(g).split(" OR ")[0]}</b>: {"poor" if poor else "intermediate"} metaboliser.',
                      'Azathioprine and mercaptopurine are used for inflammatory bowel disease, autoimmune conditions, transplants and leukaemia.',
                      ('Normal doses can cause life-threatening bone-marrow suppression. Guidelines advise about a 10-fold lower dose given 3 times a week, or another drug.' if poor else
                       'Normal doses more often lower the white blood cells. Guidelines advise starting at 30–80% of the normal dose.'),
                      'Mention this before any of these medicines is started. Doctors often test this enzyme anyway.',
                      [f'<b>Azathioprine, mercaptopurine</b>', 'Much lower dose or another drug' if poor else 'Start at 30–80% of normal dose', f'{g} {"poor" if poor else "intermediate"} metaboliser']))
        elif p: normal.append(f'{g} (thiopurines)')

    # ---------------- DPYD: fluorouracil, capecitabine
    dp = ph('DPYD')
    if 'Poor' in dp or 'Intermediate' in dp:
        poor = 'Poor' in dp
        add(_item('act', 'Chemotherapy: fluorouracil and capecitabine (DPYD)', f'<b>DPYD</b>: {"poor" if poor else "intermediate"} metaboliser.',
                  'These chemotherapy drugs (used for bowel, breast and other cancers) are broken down by the DPD enzyme.',
                  ('Standard doses can be fatal. Guidelines advise avoiding these drugs.' if poor else 'Standard doses cause severe side effects much more often. Guidelines advise starting at about half the dose.'),
                  'Very important to mention before any chemotherapy. Many cancer centres test DPYD anyway.',
                  ['<b>Fluorouracil, capecitabine</b>', 'Avoid' if poor else 'Start at about 50% dose', f'DPYD {"poor" if poor else "intermediate"} metaboliser']))
    elif dp: normal.append('DPYD (fluorouracil chemotherapy)')

    # ---------------- UGT1A1: irinotecan, atazanavir; Gilbert syndrome
    u = ph('UGT1A1')
    if 'Poor' in u:
        add(_item('know', 'Gilbert syndrome and irinotecan (UGT1A1)', f'<b>UGT1A1 {dip("UGT1A1").split(" OR ")[0]}</b>: poor metaboliser.',
                  'This is the gene type behind Gilbert syndrome (about 1 in 10 people): harmless, slightly raised bilirubin that can make the eyes a little yellow when fasting or ill.',
                  'Irinotecan (a chemotherapy drug) and atazanavir (an HIV drug) build up more; doctors lower the irinotecan dose.',
                  'Mention it if a blood test shows raised bilirubin (it explains it) or before irinotecan.',
                  ['Irinotecan; atazanavir', 'Irinotecan: lower starting dose; atazanavir: consider alternative', 'UGT1A1 poor metaboliser (Gilbert type)']))
    elif u: normal.append('UGT1A1')

    # ---------------- CYP3A5: tacrolimus
    c35 = ph('CYP3A5')
    if 'Normal' in c35 or 'Intermediate' in c35:
        add(_item('act', 'Tacrolimus (transplant medicine)', f'<b>CYP3A5 {dip("CYP3A5").split(" OR ")[0]}</b>: you make the CYP3A5 enzyme ({c35.lower()}).',
                  'Tacrolimus prevents transplant rejection. CYP3A5 makers clear it faster.',
                  'Guidelines advise a starting dose 1.5–2 times the usual, then adjusting by blood levels.',
                  'Only relevant after an organ transplant.', ['Tacrolimus', 'Higher starting dose (1.5–2×), then blood levels', f'CYP3A5 {c35.lower()}']))
    elif c35: normal.append('CYP3A5 (typical non-expresser)')

    # ---------------- CYP2B6: efavirenz
    b6 = ph('CYP2B6')
    if 'Poor' in b6:
        add(_item('act', 'Efavirenz (HIV medicine)', '<b>CYP2B6</b>: poor metaboliser.', 'Efavirenz builds up and causes more dizziness and sleep problems.',
                  'Guidelines advise a lower dose (400 or 200 mg).', 'Only relevant for HIV treatment.', ['Efavirenz', 'Lower dose (200–400 mg)', 'CYP2B6 poor metaboliser']))

    # ---------------- RYR1 / CACNA1S: malignant hyperthermia
    for g in ('RYR1', 'CACNA1S'):
        if 'Malignant Hyperthermia Susceptible' in ph(g) and 'Uncertain' not in ph(g):
            add(_item('act', 'General anaesthesia: malignant hyperthermia risk', f'A <b>{g}</b> variant linked to malignant hyperthermia was found.',
                      'Some anaesthetic gases and succinylcholine can trigger a dangerous rise in body temperature in susceptible people.',
                      'This is rare but life-threatening, and fully avoidable with other anaesthetics.',
                      'Tell every anaesthetist before surgery. Confirm with a clinical test.',
                      ['<b>Volatile anaesthetics, succinylcholine</b>', '<b>Avoid</b>; use non-triggering anaesthesia', f'{g} malignant hyperthermia variant']))

    # ---------------- G6PD (PharmCAT also calls it; markers.py words it for the person)
    if 'Deficient' in ph('G6PD'):
        cards.append(['<b>Rasburicase, primaquine, dapsone, high-dose aspirin, some sulfa drugs</b>', 'Avoid or use with caution', 'G6PD deficient'])
    elif ph('G6PD'): normal.append('G6PD')

    # ---------------- NAT2 slow acetylator
    n2 = ph('NAT2')
    if 'Poor' in n2:
        add(_item('know', 'Isoniazid and hydralazine (NAT2 slow acetylator)', '<b>NAT2</b>: slow acetylator, like about half of Europeans.',
                  'NAT2 breaks down isoniazid (tuberculosis) and hydralazine (blood pressure).', 'Slow acetylators have more side effects (liver, nerves) at standard isoniazid doses.',
                  'Mention it if isoniazid is prescribed.', ['Isoniazid; hydralazine', 'Consider lower dose and monitoring', 'NAT2 slow acetylator']))
    elif n2: normal.append('NAT2' + (' (intermediate, common and rarely matters)' if 'Intermediate' in n2 else ''))

    return items, cards, normal


def hla_has(hla, locus, allele):
    """True/False from HLA typing (2-field match), None when that locus was not typed."""
    x = (hla or {}).get(locus)
    if not x or not x.get('confident', True): return None  # low-confidence typing: fall back on tag SNPs
    return allele in (x['allele1'], x['allele2'])
