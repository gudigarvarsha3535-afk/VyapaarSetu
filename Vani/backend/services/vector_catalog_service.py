"""
Vector & DSA Catalog Service for Vani
Indexes kannada_general_store_vector_seed_1000plus.jsonl using:
- O(1) Hash Map for exact & normalized phrase matching
- Inverted Token Index for multi-word search
- RapidFuzz Vector String Matching for Kanglish phonetic & spelling variants
- Seed Phrase-Type Intent Classifier
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

SEED_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "kannada_general_store_vector_seed_1000plus.jsonl"

KANNADA_NUMBER_MAP = {
    # Kannada Script
    "ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5,
    "ಆರು": 6, "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9, "ಹತ್ತು": 10,
    "ಹನ್ನೊಂದು": 11, "ಹನ್ನೆರಡು": 12, "ಹದಿಮೂರು": 13, "ಹದಿನಾಲ್ಕು": 14, "ಹದಿನೈದು": 15,
    "ಹದಿನಾರು": 16, "ಹದಿನೇಳು": 17, "ಹದಿನೆಂಟು": 18, "ಹತ್ತೊಂಬತ್ತು": 19,
    "ಇಪ್ಪತ್ತು": 20, "ಇಪ್ಪತ್ತೈದು": 25, "ಮೂವತ್ತು": 30, "ನಲವತ್ತು": 40, "ಐವತ್ತು": 50,
    "ಅರವತ್ತು": 60, "ಅರವತ್ತೇಳು": 67, "ಎಪ್ಪತ್ತು": 70, "ಎಂಬತ್ತು": 80, "ತೊಂಬತ್ತು": 90,
    "ನೂರು": 100, "ಇನ್ನೂರು": 200, "ಐನೂರು": 500, "ಸಾವಿರ": 1000,
    
    # Kanglish / Transliteration
    "ondu": 1, "ond": 1, "vandu": 1, "wond": 1, "wondu": 1,
    "eradu": 2, "erad": 2, "yeradu": 2, "yerad": 2,
    "mooru": 3, "muru": 3, "moor": 3, "mur": 3,
    "naalku": 4, "nalku": 4, "nallu": 4, "naku": 4,
    "aidu": 5, "aiydu": 5, "aydu": 5, "ayidu": 5, "eidu": 5,
    "aaru": 6, "aru": 6, "aar": 6,
    "yelu": 7, "eelu": 7, "elu": 7, "yeelu": 7,
    "entu": 8, "yentu": 8, "enthu": 8,
    "ombattu": 9, "ombath": 9, "ombathu": 9, "wombattu": 9,
    "hattu": 10, "hathu": 10, "hath": 10, "patthu": 10, "pathu": 10,
    "hannondu": 11, "hanond": 11, "hanneradu": 12, "hannerad": 12,
    "hadimooru": 13, "hadimuru": 13, "hadinaalku": 14, "hadinalku": 14,
    "hadinaidu": 15, "hadinaydu": 15, "hadinaaru": 16, "hadinaru": 16,
    "hadinelu": 17, "hadineelu": 17, "hadinentu": 18, "hattombattu": 19,
    "ippattu": 20, "ipattu": 20, "ippath": 20, "ipath": 20, "ippathu": 20, "ipathu": 20,
    "moovattu": 30, "muvattu": 30, "moovath": 30, "muvath": 30,
    "nalavattu": 40, "nalvattu": 40, "nalvath": 40,
    "aivattu": 50, "aivath": 50, "ayvattu": 50, "ayvath": 50, "ebattu": 50,
    "aravattu": 60, "arvattu": 60, "aravath": 60, "arvath": 60,
    "eppattu": 70, "yeppattu": 70, "eppath": 70, "yeppath": 70,
    "embattu": 80, "yembattu": 80, "embath": 80, "yembath": 80,
    "tombattu": 90, "thombattu": 90, "tombath": 90, "thombath": 90,
    "nooru": 100, "nuru": 100, "noor": 100, "nur": 100,
    "innooru": 200, "innuru": 200,
    "ainooru": 500, "ainuru": 500,
    "savira": 1000, "saavira": 1000, "savir": 1000,
}

# Auto-generate compound decades (21-99, e.g. arvatyelu -> 67, ippattondu -> 21)
_DECADES = {
    20: ["ippatt", "ipatt", "ipat", "ippat"],
    30: ["moovatt", "muvatt", "moovat", "muvat"],
    40: ["nalavatt", "nalvatt", "nalvat"],
    50: ["aivatt", "ayvatt", "aivat", "ayvat"],
    60: ["aravatt", "arvatt", "arvat", "arvaty", "aravat"],
    70: ["eppatt", "yeppatt", "epatt", "yepatt", "epat", "yepat"],
    80: ["embatt", "yembatt", "embat", "yembat"],
    90: ["tombatt", "thombatt", "tombat", "thombat"]
}
_UNITS = {
    1: ["ondu", "ond"],
    2: ["eradu", "erad", "yeradu", "yerad"],
    3: ["mooru", "muru", "moor"],
    4: ["naalku", "nalku"],
    5: ["aidu", "aydu", "aiydu"],
    6: ["aaru", "aru"],
    7: ["elu", "yelu", "eelu"],
    8: ["entu", "yentu"],
    9: ["ombattu", "ombath", "ombathu"]
}
for _d_val, _d_prefixes in _DECADES.items():
    for _u_val, _u_suffixes in _UNITS.items():
        _tot = _d_val + _u_val
        for _p in _d_prefixes:
            for _s in _u_suffixes:
                KANNADA_NUMBER_MAP[_p + _s] = _tot
                if _p.endswith("y") and _s.startswith("y"):
                    KANNADA_NUMBER_MAP[_p[:-1] + _s] = _tot

def normalize_numbers(text: str) -> str:
    """Normalizes Kannada script and Kanglish number words into standard digits."""
    res = text
    for w in sorted(KANNADA_NUMBER_MAP.keys(), key=lambda x: -len(x)):
        if all(ord(c) < 128 for c in w):
            pat = r'\b' + re.escape(w) + r'\b'
        else:
            pat = r'(?:(?<=^)|(?<=\s)|(?<=[.,!?]))' + re.escape(w) + r'(?=$|\s|[.,!?])'
        res = re.sub(pat, str(KANNADA_NUMBER_MAP[w]), res, flags=re.IGNORECASE)
    return res

CURATED_BRAND_ALIASES = {
    "hershey": ("Chocolate syrup", "Baking"),
    "hersheys": ("Chocolate syrup", "Baking"),
    "hershy": ("Chocolate syrup", "Baking"),
    "hershys": ("Chocolate syrup", "Baking"),
    "hershey's": ("Chocolate syrup", "Baking"),
    "hershy's": ("Chocolate syrup", "Baking"),
    "choclate syrup": ("Chocolate syrup", "Baking"),
    "chocolate syrup": ("Chocolate syrup", "Baking"),
    "sakkare": ("Sugar", "Baking"),
    "sugar": ("Sugar", "Baking"),
    "idli rave": ("Rava / semolina", "Grains & Flours"),
    "rave": ("Rava / semolina", "Grains & Flours"),
    "rava": ("Rava / semolina", "Grains & Flours"),
    "neerina bottle": ("Water bottle", "Beverages"),
    "neerina bottles": ("Water bottle", "Beverages"),
    "neeru bottle": ("Water bottle", "Beverages"),
    "ಅಕ್ಕಿ": ("Sona Masoori Rice (Akki)", "Grocery / grains"),
    "ಬಾಸುಮತಿ ರೈಸ್": ("Basmati rice", "Grocery / grains"),
    "ಬಾಸುಮತಿ": ("Basmati rice", "Grocery / grains"),
    "ಬಾಸ್ಮತಿ ರೈಸ್": ("Basmati rice", "Grocery / grains"),
    "ಬಾಸ್ಮತಿ": ("Basmati rice", "Grocery / grains"),
    "ಸಕ್ಕರೆ": ("Sugar", "Baking"),
    "ಟೊಮೆಟೊ": ("Fresh Tomato (Tamota)", "Vegetables"),
    "ಬೆಳ್ಳುಳ್ಳಿ": ("Fresh Garlic (Bellulli)", "Vegetables"),
    "ತುಪ್ಪ": ("Nandini Pure Ghee", "Dairy"),
}

COMMERCE_STOPWORDS = {
    "rate", "bele", "dar", "price", "stock", "packet", "packets", "pack", "piece", "pieces",
    "box", "boxes", "bag", "bags", "bottle", "bottles", "batli", "dabba", "dabbagalu",
    "tin", "tins", "can", "cans", "pouch", "pouches", "sachet", "sachets", "strip", "strips",
    "cup", "cups", "cheela", "chila", "kattu", "kattugalu", "nag", "nagalu",
    "kg", "g", "gm", "ml", "l", "litre", "liter", "ide", "ideya", "illa",
    "mugidide", "mugithu", "khali", "khaliaagide", "kali", "kaali", "kaliagide", "kaaliagide",
    "maadi", "kodi", "serisi", "add", "ge", "na", "alli",
    "eshtu", "yestu", "yava", "yavudu", "yavellam", "which", "what", "enu", "discount", "off", "offer",
    "riyayiti", "order", "ord", "item", "items", "saraku", "bandide", "bandive", "arrived",
    "bantu", "tulpiside", "delivery", "delivered", "raddu", "cancel", "packed", "bidi", "helu", "beku",
    "haaki", "thegedu", "delete", "remove", "thege", "thegiri", "thegisi", "today", "sales", "report", "vyapara", "vyapaara", "business", "ivattu",
    "galu", "slice", "slices", "rs", "rupayi",
    "ಎಷ್ಟು", "ಏನು", "ಹೇಳಿ", "ಕೊಡಿ", "ತಿಳಿಸಿ", "ಬೆಲೆ", "ರೇಟ್", "ದರ", "ರೂಪಾಯಿ", "ರೂ",
    "ರುಪಾಯಿ", "ರುಪೀಸ್", "ಮಾಡಿ", "ಹಾಕಿ", "ಮಾಡಬೇಕು", "ಆಗಿದೆ", "ಬಂದಿದೆ", "ಬಂದಿವೆ",
    "ಬಂತು", "ಇದೆ", "ಲಭ್ಯವಿದೆ", "ಪ್ಯಾಕೆಟ್", "ಪ್ಯಾಕೆಟ್ಸ್", "ಕೆಜಿ", "ಗ್ರಾಂ", "ಲೀಟರ್", "ನ",
    "ಡಿಸ್ಕೌಂಟ್", "ರಿಯಾಯಿತಿ", "ಆಫರ್"
}

class VectorCatalogService:
    def __init__(self, seed_path: Optional[Path] = None):
        self.seed_path = seed_path or SEED_FILE_PATH
        self.exact_map: Dict[str, Dict[str, Any]] = {}
        self.canonical_products: Dict[str, Dict[str, Any]] = {}
        self.token_index: Dict[str, List[Dict[str, Any]]] = {}
        self.alias_list: List[str] = []
        self.alias_to_entry: Dict[str, Dict[str, Any]] = {}
        self.lexical_vocab: Dict[str, str] = {}
        self.is_loaded = False
        
        self.load_seed_data()

    def load_seed_data(self):
        if not self.seed_path.exists():
            logger.warning(f"Vector seed file not found at {self.seed_path}")
            return

        try:
            with open(self.seed_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    alias = record.get("alias", "").strip()
                    if not alias:
                        continue

                    lower_alias = alias.lower()
                    canon = record.get("canonical_product", alias)
                    category = record.get("category", "General")
                    alias_type = record.get("alias_type", "alias")

                    # 1. Exact Map
                    self.exact_map[lower_alias] = record
                    self.alias_to_entry[lower_alias] = record

                    is_vocab = (category == "Language / shop vocabulary" or alias_type == "intent-or-lexical-alias")
                    if is_vocab:
                        self.lexical_vocab[lower_alias] = canon
                    else:
                        self.alias_list.append(lower_alias)

                    # 2. Canonical Product Registry
                    if canon not in self.canonical_products:
                        self.canonical_products[canon] = {
                            "name": canon,
                            "category": category,
                            "aliases": set()
                        }
                    self.canonical_products[canon]["aliases"].add(lower_alias)

                    # 3. Inverted Token Index (filter out stop words and numbers)
                    if not is_vocab:
                        tokens = re.findall(r"[\w\u0C80-\u0CFF]+", lower_alias)
                        for tok in tokens:
                            if len(tok) >= 2 and tok not in COMMERCE_STOPWORDS and not tok.isdigit():
                                if tok not in self.token_index:
                                    self.token_index[tok] = []
                                self.token_index[tok].append(record)

            self.is_loaded = True
            logger.info(f"Loaded {len(self.exact_map)} vector seed aliases across {len(self.canonical_products)} canonical products.")
        except Exception as e:
            logger.error(f"Failed to load vector seed file: {e}")

    def find_canonical_product(self, query: str) -> Optional[Tuple[str, str, float]]:
        """
        Uses O(1) hash lookup, token intersection, and RapidFuzz vector scoring
        to find the closest canonical product and category.
        Returns: (canonical_name, category, confidence_score)
        """
        if not query or not query.strip():
            return None

        q_lower = query.lower().strip()

        # 0. Curated Brand / Transliteration Aliases (e.g. Hershey's, Sakkare, Idli rave)
        q_no_punct = re.sub(r"['’\".,]", "", q_lower).strip()
        for calias, (cname, ccat) in sorted(CURATED_BRAND_ALIASES.items(), key=lambda x: -len(x[0])):
            calias_clean = re.sub(r"['’\".,]", "", calias).strip()
            if calias in q_lower or calias_clean in q_no_punct:
                return cname, ccat, 1.0
            if all(ord(c) < 128 for c in calias) and (re.search(r'\b' + re.escape(calias) + r'\b', q_lower) or re.search(r'\b' + re.escape(calias_clean) + r'\b', q_no_punct)):
                return cname, ccat, 1.0

        # 1. O(1) Direct Exact Lookup
        if q_lower in self.exact_map:
            entry = self.exact_map[q_lower]
            if entry.get("category") != "Language / shop vocabulary":
                return entry["canonical_product"], entry["category"], 1.0

        # Extract clean non-stopword tokens
        raw_tokens = re.findall(r"[\w\u0C80-\u0CFF]+", q_lower)
        clean_tokens = [t for t in raw_tokens if t not in COMMERCE_STOPWORDS and not t.isdigit()]
        clean_q = " ".join(clean_tokens)

        # 2. Word Boundary Matching against known product aliases (longest alias first)
        for alias in sorted(self.exact_map.keys(), key=lambda x: -len(x)):
            if self.exact_map[alias].get("category") == "Language / shop vocabulary":
                continue
            if len(alias) >= 3 and re.search(r'\b' + re.escape(alias) + r'\b', q_lower):
                entry = self.exact_map[alias]
                return entry["canonical_product"], entry["category"], 0.95

        # 3. Token-based Candidate Intersection
        if clean_tokens:
            candidate_canonicals: Dict[str, int] = {}
            candidate_categories: Dict[str, str] = {}

            for tok in clean_tokens:
                if tok in self.token_index:
                    for entry in self.token_index[tok]:
                        cp = entry["canonical_product"]
                        candidate_canonicals[cp] = candidate_canonicals.get(cp, 0) + 1
                        candidate_categories[cp] = entry["category"]

            if candidate_canonicals:
                best_cp = max(candidate_canonicals, key=candidate_canonicals.get)
                return best_cp, candidate_categories[best_cp], 0.90

        # 4. RapidFuzz Vector String Matching (top similarity match)
        target_str = clean_q if clean_q else q_lower
        if target_str and self.alias_list:
            match = process.extractOne(
                target_str,
                self.alias_list,
                scorer=fuzz.token_set_ratio,
                score_cutoff=75
            )
            if match:
                matched_alias, score, _ = match
                entry = self.alias_to_entry[matched_alias]
                return entry["canonical_product"], entry["category"], score / 100.0

        return None

    def get_context_for_llm(self, query: str) -> str:
        """
        Extracts relevant vocabulary and candidate products from vector seed to ground the LLM.
        """
        match = self.find_canonical_product(query)
        if match:
            canon, cat, score = match
            return f"Known Store Item Match: '{canon}' (Category: '{cat}', Match Confidence: {score:.2f})."
        return "No specific catalog match found in seed."

vector_catalog = VectorCatalogService()
