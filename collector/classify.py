"""Classification for NAND flash papers (bibliographic only: no figures are extracted).

Pure functions (no network, no files) so they can be unit-tested and re-run over the
cached records whenever the rules change. Abstracts are inputs only; they are never
written to the output.
"""
import re

I = re.IGNORECASE

# ---------------------------------------------------------------- relevance
NAND_PAT = re.compile(
    r"\bNAND\b|\bV-?NAND\b|\b3-?D\s*NAND|"
    r"\bflash (?:memor(?:y|ies)|storage|cells?|arrays?|chips?|devices?|controllers?|SSDs?|products?)\b|"
    r"\bflash[- ]based (?:SSD|storage|solid)|\bSSDs?\b|solid[- ]state (?:drives?|disks?|storage)|"
    r"charge[- ]trap(?:ping)?[- ](?:flash|memory|memories|cells?|layer|transistors?|NAND)|"
    r"floating[- ]gate (?:flash|memory|memories|cells?|transistors?|NAND)|"
    r"\bpage buffers?\b|\bstring select|\bmulti[- ]?level[- ]cell flash|\b(?:SLC|MLC|TLC|QLC|PLC) (?:flash|NAND|memory|SSD)|"
    r"\b\d+\s*(?:-?\s*)?(?:layer|stack(?:ed)?|WL)s?\b[^.;]{0,40}\b(?:flash|NAND)", I)

# logic gates, flash converters, camera/lidar flashes, and NOR-only or embedded flash are out of scope
NOT_NAND = re.compile(
    r"\bNAND[- ]?(?:gates?|logic|cells? library|based logic|tree)\b|\bNOR/NAND\b|\bNAND/NOR\b|"
    r"\bflash (?:ADCs?|A/D|analog[- ]to[- ]digital|converters?|quanti[sz]er|comparators?|TDCs?|lidar|LiDAR|lamps?|light|imag|photograph)|"
    r"\bflash[- ]sar\b|two[- ]step flash|sub[- ]ranging flash|\bflash X[- ]?ray", I)
NOR_ONLY = re.compile(r"\bNOR (?:flash|memory|array)|embedded flash|\beFlash\b|split[- ]gate flash|\bMCU\b|microcontroller", I)
SSD_ONLY = re.compile(r"\bSSDs?\b|solid[- ]state (?:drives?|disks?|storage)", I)

NON_PAPER = re.compile(
    r"^(front cover|back cover|table of contents|contents|author index|index|"
    r"call for papers|editorial|guest editorial|reviewers|session \d+ overview|"
    r"(?:tutorials?|short course|evening (?:event|session)|forum|panel)(?=\s*:|\s*$)|"
    r"(ieee )?(transactions|journal) .*information|blank page|copyright)\b", I)

ABS_PAT = re.compile(r"\bNAND\b|flash memor|\bV-?NAND\b|3-?D\s*NAND|charge[- ]trap flash", I)


def relevance(title, abstract):
    """'core' (NAND is the subject), 'related' (only in the abstract, or an SSD/storage paper
    without NAND in the title) or None."""
    t = title or ""
    a = abstract or ""
    if NOT_NAND.search(t) and not re.search(r"\bNAND flash|flash memor", t, I):
        return None
    if NAND_PAT.search(t):
        if NOR_ONLY.search(t) and not re.search(r"\bNAND\b", t, I):
            return None
        if SSD_ONLY.search(t) and not re.search(r"\bNAND\b|flash", t, I):   # SSD system paper: NAND is underneath
            return "related" if ABS_PAT.search(a) else None
        return "core"
    if ABS_PAT.search(a) and not NOT_NAND.search(t) and not NOR_ONLY.search(t):
        return "related"
    return None


# ---------------------------------------------------------------- topics
TOPIC_RULES = [
    ("Chip",                 r"\b\d+\s*-?\s*(?:Gb|Tb|Gbit|Tbit)\b|\b\d+\s*-?\s*(?:layers?|stack(?:ed)?|WL)\b|"
                             r"\bbits?/cell\b|\b\d\s*b/cell|\b(?:SLC|MLC|TLC|QLC|PLC)\b|\bdie\b|\bV-?NAND\b|NAND flash memory\b"),
    ("Sensing/page buffer",  r"\bsens(?:e|ing)\b|sense amp|page buffer|bit[- ]?line|\bBL\b|read (?:circuit|scheme|path)|"
                             r"cell current|reference current"),
    ("HV/WL driver",         r"charge[- ]pump|high[- ]voltage|\bHV\b|word[- ]?line (?:driver|decoder|bias|voltage|ramp)|\bWL (?:driver|decoder)|"
                             r"row decoder|voltage (?:regulator|generator)|power (?:management|delivery|supply)|\bLDO\b|peak current"),
    ("I/O interface",        r"\bI/?O\b|interface|\bToggle\b|\bONFI\b|\bMT/s\b|Gb/s/pin|\bDQ\b|\bZQ\b|transceiver|"
                             r"duty[- ]cycle|\bDCC\b|\bDLL\b|training|signal integrity|equaliz"),
    ("Program/erase scheme", r"\bprogram(?:ming)?\b|\berase\b|\bISPP\b|verify|read[- ]retry|incremental step|"
                             r"\bwrite (?:scheme|speed|performance|throughput)|\btPROG\b|\btR\b|read latency|algorithm"),
    ("Controller/ECC/SSD",   r"controller|\bECC\b|\bLDPC\b|\bBCH\b|error[- ]correct|soft[- ]decision|\bFTL\b|"
                             r"flash translation|\bSSDs?\b|solid[- ]state (?:drive|disk|storage)|storage system|wear[- ]leveling|garbage collection"),
    ("Reliability",          r"retention|endurance|disturb|reliabilit|interference|variation|\bRTN\b|random telegraph|"
                             r"cycling|degradation|threshold[- ]voltage (?:shift|distribution)|\bVth (?:shift|distribution)|lateral migration|read noise"),
    ("Device/cell",          r"charge[- ]trap|floating[- ]gate|\bSONOS\b|\bTANOS\b|channel (?:hole|material)|poly(?:crystalline)?[- ]?si|"
                             r"\bIGZO\b|oxide semiconductor|ferroelectric|\bFe-?NAND\b|\bFeFET\b|tunnel (?:oxide|dielectric)|gate[- ]all[- ]around|"
                             r"\bcell (?:structure|design|scaling)|\bCMOS[- ]under[- ]array|\bCUA\b|\bCOP\b|\bPUC\b|wafer bonding|\bXtacking\b|hybrid bonding|"
                             r"\bscaling\b|fabricat|\bprocess integration|\bdevices?\b(?! driver)"),
    ("Compute/search",       r"in[- ]memory comput|computing[- ]in[- ]memory|\bCIM\b|\bPIM\b|in[- ]storage comput|near[- ](?:storage|memory) comput|"
                             r"neural|\bDNN\b|\bCNN\b|deep learning|machine learning|\bAI\b|\bLLM\b|transformer|vector (?:search|database)|"
                             r"\bsearch\b|content[- ]addressable|\bCAM\b|hyperdimensional"),
]
TOPIC_RX = [(n, re.compile(p, I)) for n, p in TOPIC_RULES]


def topics(title, abstract):
    """Topic tags from the title; the first two abstract sentences only add tags the title
    cannot show (comparisons later in an abstract describe other work)."""
    tags = [n for n, rx in TOPIC_RX if rx.search(title or "")]
    if abstract:
        first = " ".join(re.split(r"(?<=[.!?])\s+", abstract)[:2])
        for n, rx in TOPIC_RX:
            if n not in tags and n not in ("Chip", "Device/cell") and rx.search(first):
                tags.append(n)
    return [n for n, _ in TOPIC_RULES if n in tags]   # stable order


# ---------------------------------------------------------------- companies (from affiliations)
COMPANIES = [
    ("Samsung",         r"samsung"),
    ("SK hynix",        r"\bsk ?hynix|\bhynix\b"),
    ("Kioxia/Toshiba",  r"kioxia|toshiba"),
    ("Western Digital", r"western digital|sandisk"),
    ("Micron",          r"micron"),
    ("Intel/Solidigm",  r"\bintel\b|solidigm"),
    ("YMTC",            r"yangtze memory|\bymtc\b"),
    ("Macronix",        r"macronix"),
    ("Other industry",  r"\binc\b|\bltd\b|\bcorp|co\.,|company|gmbh|\bllc\b|\bs\.a\.|\bag\b"),
]
COMPANY_RX = [(n, re.compile(p, I)) for n, p in COMPANIES]


def companies(affiliations):
    out = []
    for aff in affiliations or []:
        for n, rx in COMPANY_RX:
            if rx.search(aff or ""):
                if n not in out:
                    out.append(n)
                break
    if "Other industry" in out and len(out) > 1:
        out.remove("Other industry")
    return out


# ------------------------------------------------------------- affiliations and dates (same rules as adc-census)
ORG_HINT = re.compile(r"universit|institut|college|school|KAIST|POSTECH|UNIST|DGIST|GIST|\bETH\b|EPFL|\bMIT\b|"
                      r"laborator|\blabs?\b|inc\b|ltd|corp|company|co\.|electronics|semiconductor|technolog|"
                      r"research|centre|center|academy|imec|tsmc|samsung|sk hynix|intel|mediatek|qualcomm|"
                      r"apple|google|huawei|broadcom|analog devices|texas instruments|kioxia|toshiba|micron|"
                      r"western digital|sandisk|macronix|yangtze|solidigm", I)


def org_and_country(aff):
    if not aff:
        return None, None
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    if not parts:
        return None, None
    country = re.sub(r"\s+\d[\d\- ]*$", "", parts[-1])
    if re.fullmatch(r"(korea|south korea|republic of korea|korea \(south\))", country, I):
        country = "South Korea"
    elif re.fullmatch(r"(usa|u\.s\.a\.|united states|united states of america|us)", country, I):
        country = "USA"
    elif re.fullmatch(r"(prc|p\.r\. china|people's republic of china)", country, I):
        country = "China"
    org = None
    for p in parts:
        if ORG_HINT.search(p) and not re.match(r"(department|dept|school of|faculty|division)\b", p, I):
            org = p
            break
    if org is None:
        org = parts[1] if len(parts) > 2 else parts[0]
    if len(country) > 30 or re.search(r"\d", country):
        country = None
    return org, country


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_month(pubdate, year):
    s = (pubdate or "").lower()
    years = re.findall(r"(?:19|20)\d{2}", s)
    y = years[-1] if years else (str(year) if year else None)
    mon = None
    for tok in re.findall(r"[a-z]{3,}", s):
        if tok[:3] in MONTHS:
            mon = MONTHS[tok[:3]]
            break
    if y and mon:
        return "%s-%02d" % (y, mon)
    return y or ""
