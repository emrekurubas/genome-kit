# Short plain-language notes on major Y-chromosome and mitochondrial haplogroups (matched by longest prefix).

Y = {
    'A': 'One of the oldest branches of the human father-line tree, found mainly in Africa.',
    'B': 'An ancient African branch, common among Central African hunter-gatherers.',
    'C': 'An early out-of-Africa branch, today common in Central and East Asia (especially Mongolia and Kazakhstan), Siberia and Oceania.',
    'D': 'An old Asian branch, frequent in Tibet, Japan and the Andaman Islands.',
    'E': 'Arose in Africa; its E1b1b branch spread around the Mediterranean, the Middle East and the Balkans with early farmers and later movements.',
    'E1b1a': 'The most common father-line in West and Central Africa, spread widely by the Bantu expansion.',
    'E1b1b': 'Common around the Mediterranean, in North and East Africa, the Middle East and the Balkans.',
    'G': 'Strongly tied to the Caucasus and Anatolia; it was common among the first Neolithic farmers who spread from Anatolia into Europe.',
    'H': 'Mainly found in South Asia and among the Roma.',
    'I': 'A European father-line going back to Ice-Age hunter-gatherers.',
    'I1': 'Common in Scandinavia and around the North Sea.',
    'I2': 'Common in the Balkans (especially the Dinaric region) and Sardinia; descended from European hunter-gatherers.',
    'J': 'A Middle Eastern father-line associated with the spread of farming from the Fertile Crescent.',
    'J1': 'Common in the Arabian Peninsula, the Levant and the North Caucasus (Dagestan).',
    'J2': 'Common in Anatolia, the Caucasus, Iran, Greece and Italy; spread with early farming and Bronze-Age civilisations.',
    'L': 'Mainly found in South Asia and among some peoples of the Middle East and Central Asia.',
    'N': 'Common in North-East Europe (Finns, Baltic peoples), Siberia and among some Turkic and Uralic-speaking peoples.',
    'O': 'The most common father-line in East and South-East Asia.',
    'Q': 'Found in Siberia, Central Asia and among most Native Americans.',
    'R': 'A large branch that expanded across Eurasia in the Bronze Age.',
    'R1a': 'Spread from the Bronze-Age Eurasian steppe; common in Eastern Europe, Central and South Asia.',
    'R1a1a1b2': 'The "Asian" Z93 branch of R1a, linked to the Bronze-Age Sintashta/Andronovo cultures, later Indo-Iranian peoples, Scythians and Turkic nomads.',
    'R1a1a1b1': 'The "European" Z283 branch of R1a, common among Slavic- and Baltic-speaking peoples and in Scandinavia.',
    'R1b': 'Spread with Bronze-Age steppe migrations; the most common father-line in Western Europe, also found in Anatolia and the Caucasus.',
    'R2': 'Found mainly in South Asia and the Caucasus.',
    'T': 'A rare branch spread thinly across the Middle East, East Africa and Europe.',
}

MT = {
    'L': 'An African mother-line; all other mother-lines branch off from it.',
    'M': 'Very common in South and East Asia and Siberia.',
    'N': 'One of the two founding out-of-Africa mother-lines; its branches cover most of West Eurasia.',
    'A': 'Found in East Asia, Siberia and among Native Americans.',
    'B': 'Found in East and South-East Asia, Polynesia and the Americas.',
    'C': 'Common in Siberia, Central Asia and the Americas.',
    'D': 'Common in East Asia, Siberia and the Americas.',
    'F': 'Common in East and South-East Asia.',
    'G': 'Found in North-East Asia and Central Asia.',
    'H': 'The most common mother-line in Europe and West Asia (about 40% of Europeans); it spread widely after the last Ice Age.',
    'HV': 'The parent branch of H and V, frequent in the Near East and the Caucasus.',
    'I': 'A small West Eurasian branch found at low frequency from Europe to Iran.',
    'J': 'Arose in the Near East and spread into Europe with early farmers.',
    'K': 'A branch of U8, common among early European farmers and today among Ashkenazi Jews and in the Near East.',
    'N1': 'A rare Near Eastern branch, found in Neolithic farmers and today across the Middle East and Europe.',
    'R': 'The large branch that contains most West Eurasian mother-lines.',
    'T': 'Spread with Neolithic farmers from the Near East into Europe.',
    'U': 'An old West Eurasian mother-line; U5 was common among European hunter-gatherers.',
    'U5': 'The classic European hunter-gatherer mother-line, still common in Finland and among the Sámi.',
    'V': 'A branch of HV, frequent among the Sámi and in Iberia.',
    'W': 'A rare branch found from Europe to South Asia.',
    'X': 'A rare branch found in the Near East, Europe, and among some Native Americans.',
    'Z': 'Found in Siberia and Central Asia.',
}


def describe(hg, table):
    if not hg: return ''
    best = ''
    for k in table:
        if hg.startswith(k) and len(k) > len(best): best = k
    return table.get(best, '')
