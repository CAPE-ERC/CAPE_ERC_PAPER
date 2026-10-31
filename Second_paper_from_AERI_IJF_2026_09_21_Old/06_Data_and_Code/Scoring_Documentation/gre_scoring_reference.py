"""Frozen GRE article-level scoring reference. Baseline measurement only."""
import re
from typing import Dict, List
import pandas as pd

try:
    from ftfy import fix_text as _ftfy_fix_text
except Exception:
    _ftfy_fix_text = None

SCORING_METHOD = 'original_article_presence_v1'
ECON_RELEVANCE_TERMS = ['economy', 'economic', 'macroeconomic', 'gdp', 'growth', 'recession', 'slowdown', 'inflation', 'prices', 'cost of living', 'consumer prices', 'cpi', 'budget', 'fiscal', 'deficit', 'surplus', 'revenue', 'tax', 'subsidy', 'debt', 'default', 'restructuring', 'bond', 'treasury', 'sovereign', 'interest rate', 'policy rate', 'central bank', 'monetary', 'currency', 'exchange rate', 'forex', 'reserves', 'balance of payments', 'import', 'export', 'trade', 'tariff', 'sanction', 'bank', 'banking', 'financial stability', 'liquidity', 'capital adequacy', 'npl', 'unemployment', 'jobs', 'layoffs', 'wages', 'imf', 'world bank', 'afdb', 'économie', 'economique', 'macroéconomie', 'pib', 'croissance', 'récession', 'ralentissement', 'inflation', 'prix', 'coût de la vie', 'indice des prix', 'budget', 'fiscal', 'déficit', 'excédent', 'recettes', 'impôt', 'taxe', 'subvention', 'dette', 'défaut', 'restructuration', 'obligation', 'souverain', "taux d'intérêt", 'banque centrale', 'monétaire', 'monnaie', 'taux de change', 'réserves', 'balance des paiements', 'importation', 'exportation', 'commerce', 'tarif', 'sanction', 'banque', 'bancaire', 'stabilité financière', 'liquidité', 'chômage', 'emplois', 'licenciements', 'economia', 'econômico', 'macroeconômico', 'pib', 'crescimento', 'recessão', 'desaceleração', 'inflação', 'preços', 'custo de vida', 'índice de preços', 'orçamento', 'fiscal', 'déficit', 'superávit', 'receita', 'imposto', 'subsídi', 'dívida', 'calote', 'incumprimento', 'reestruturação', 'título', 'soberano', 'taxa de juros', 'banco central', 'monetário', 'moeda', 'câmbio', 'reservas', 'balança de pagamentos', 'importação', 'exportação', 'comércio', 'tarifa', 'sanção', 'banco', 'bancário', 'estabilidade financeira', 'liquidez', 'desemprego', 'empregos', 'demissões']
PILLARS: Dict[str, List[str]] = {'InflationRisk': ['inflation', 'price hike', 'cost of living', 'shortage', 'scarcity', 'hausse des prix', 'pénurie', 'inflação', 'escassez'], 'FXExternalRisk': ['exchange rate', 'currency', 'devaluation', 'forex', 'reserves', 'taux de change', 'dévaluation', 'câmbio', 'desvalorização'], 'DebtFiscalRisk': ['debt', 'default', 'restructuring', 'bond', 'budget deficit', 'dette', 'défaut', 'reestruturação', 'dívida'], 'FinancialSectorRisk': ['bank', 'liquidity', 'bank run', 'npl', 'insolvency', 'banque', 'liquidité', 'corrida bancária', 'insolvência'], 'GrowthRealEconomyRisk': ['recession', 'slowdown', 'contraction', 'unemployment', 'layoffs', 'récession', 'chômage', 'recessão', 'desemprego'], 'CommoditySupplyRisk': ['oil shock', 'fuel scarcity', 'supply disruption', 'logistics disruption', 'choc pétrolier', 'pénurie de carburant', 'escassez de combustível'], 'PoliticalEconomyRisk': ['protest', 'unrest', 'coup', 'strike', 'sanction', 'manifestation', "coup d'état", 'greve', 'golpe'], 'ClimateDisasterRisk': ['drought', 'flood', 'cyclone', 'heatwave', 'crop failure', 'sécheresse', 'inondation', 'seca', 'inundação']}
SEVERITY_TIER_TERMS: Dict[int, List[str]] = {1: ['pressure', 'concern', 'moderate', 'slight', 'risk', 'uncertainty', 'pression', 'inquiétude', 'risque', 'incertitude', 'pressão', 'preocupação', 'risco', 'incerteza'], 2: ['rising', 'worsening', 'strain', 'surge', 'spike', 'sharp increase', 'deterioration', 'hausse', 'aggravation', 'tension', 'détérioration', 'aumentando', 'piorando', 'deterioração'], 3: ['crisis', 'collapse', 'severe', 'emergency', 'panic', 'distress', 'acute shortage', 'crise', 'effondrement', 'grave', 'urgence', 'panique', 'pénurie aiguë', 'crise', 'colapso', 'grave', 'emergência', 'pânico'], 4: ['default', 'hyperinflation', 'bank run', 'sovereign default', 'meltdown', 'economic collapse', 'défaut', 'hyperinflation', 'panique bancaire', 'défaut souverain', 'calote', 'hiperinflação', 'corrida bancária']}
TITLE_RISK_HINTS = ['crisis', 'default', 'devaluation', 'inflation', 'shortage', 'collapse', 'debt', 'restructuring', 'recession', 'bank', 'emergency', 'crise', 'défaut', 'dévaluation', 'inflation', 'pénurie', 'effondrement', 'dette', 'restructuration', 'récession', 'banque', 'urgence', 'crise', 'calote', 'desvalorização', 'inflação', 'escassez', 'colapso', 'dívida', 'reestruturação', 'recessão', 'banco', 'emergência']

def _norm(s):
    s = str(s or "")
    if _ftfy_fix_text is not None:
        s = _ftfy_fix_text(s)
    return re.sub(r"\s+", " ", s).strip()

def _rx(terms):
    parts = []
    for term in terms:
        q = re.escape(str(term).strip()).replace(r"\ ", r"\s+")
        if q:
            parts.append(rf"\b{q}\b")
    return re.compile("|".join(parts) if parts else r"(?!x)x", re.IGNORECASE)

RE_ECON = _rx(ECON_RELEVANCE_TERMS)
RE_PILLARS = {k: _rx(v) for k, v in PILLARS.items()}
RE_SEVERITY = {k: _rx(v) for k, v in SEVERITY_TIER_TERMS.items()}
RE_TITLE_HINTS = _rx(TITLE_RISK_HINTS)

def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    title = df["title"].astype(str).map(_norm)
    text = df["text"].astype(str).map(_norm)
    full = (title + " " + text).str.lower()
    relevance = full.str.contains(RE_ECON, regex=True).astype("int8")
    severity = pd.Series(0, index=df.index, dtype="int16")
    rel_idx = relevance[relevance.eq(1)].index
    if len(rel_idx):
        rel_text = full.loc[rel_idx]
        sev = pd.Series(1, index=rel_idx, dtype="int16")
        for tier in sorted(RE_SEVERITY):
            hits = rel_text.str.contains(RE_SEVERITY[tier], regex=True)
            sev.loc[hits[hits].index] = tier
        severity.loc[rel_idx] = sev
    counts = {k: full.str.count(rx.pattern).astype("int16") for k, rx in RE_PILLARS.items()}
    pillar_df = pd.DataFrame(counts, index=df.index)
    active = (pillar_df > 0).sum(axis=1).astype("int16")
    weight = (1.0
              + title.str.lower().str.contains(RE_TITLE_HINTS, regex=True).astype("float32") * 0.5
              + (text.str.len() >= 1200).astype("float32") * 0.2
              + (active >= 2).astype("float32") * 0.3).clip(1.0, 2.0)
    article_score = relevance.astype("float32") * severity.astype("float32") * weight.astype("float32")
    out = pd.DataFrame({"relevance": relevance, "severity": severity, "weight": weight, "article_score": article_score, "pillar_active_count": active}, index=df.index)
    for key in PILLARS:
        out[key] = pillar_df[key].gt(0).astype("int8")
    out["GRE_article_contribution"] = out["article_score"] * out["GrowthRealEconomyRisk"]
    return out
