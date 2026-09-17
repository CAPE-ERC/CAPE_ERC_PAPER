# aeri_from_news_fast.py
# -----------------------------------------------------------------------------
# FAST AERI computed from:
#   SCRAPE_ROOT/Country/Site/YYYY-MM/articles_*.csv.gz
#
# Speedups:
#  - parallel per-file processing (multiprocessing)
#  - read only needed columns (usecols)
#  - vectorized scoring (no row-wise apply)
#
# Output:
#  - aeri_country_period.csv
#  - aeri_pillars_country_period.csv
#  - aeri_diagnostics.csv
# -----------------------------------------------------------------------------

import os
import re
import gzip
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterable, Set, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from pandas.errors import EmptyDataError

try:
    from ftfy import fix_text as _ftfy_fix_text
except Exception:
    _ftfy_fix_text = None


# =============================================================================
# ✅ USER SETTINGS (EDIT ONCE)
# =============================================================================
SCRAPE_ROOT = Path(r"G:\My Drive\News_Articles_Africa_Workbook\EPU\Scrapped_Articles")
OUT_DIR = Path(__file__).resolve().parent / "AERI_OUTPUT"
SCORING_METHOD = "original_article_presence_v1"

DEFAULT_PERIOD   = "month"   # month | week | day
DEFAULT_DATE_COL = None      # e.g. "date"
USE_PROMPTING = True

ENCODING = "utf-8"
PROGRESS_EVERY_N_FILES = 50

# Parallel workers (None -> use CPU-1)
MAX_WORKERS = None

# If your files are huge and memory is tight, set True:
LOW_MEMORY_MODE = False


# =============================================================================
# 1) KEYWORD TAXONOMY (keep as you have; can expand per-country later)
# =============================================================================
ECON_RELEVANCE_TERMS = [
    # English
    "economy","economic","macroeconomic","gdp","growth","recession","slowdown",
    "inflation","prices","cost of living","consumer prices","cpi",
    "budget","fiscal","deficit","surplus","revenue","tax","subsidy",
    "debt","default","restructuring","bond","treasury","sovereign",
    "interest rate","policy rate","central bank","monetary",
    "currency","exchange rate","forex","reserves","balance of payments",
    "import","export","trade","tariff","sanction",
    "bank","banking","financial stability","liquidity","capital adequacy","npl",
    "unemployment","jobs","layoffs","wages",
    "imf","world bank","afdb",

    # French
    "économie","economique","macroéconomie","pib","croissance","récession","ralentissement",
    "inflation","prix","coût de la vie","indice des prix",
    "budget","fiscal","déficit","excédent","recettes","impôt","taxe","subvention",
    "dette","défaut","restructuration","obligation","souverain",
    "taux d'intérêt","banque centrale","monétaire",
    "monnaie","taux de change","réserves","balance des paiements",
    "importation","exportation","commerce","tarif","sanction",
    "banque","bancaire","stabilité financière","liquidité",
    "chômage","emplois","licenciements",

    # Portuguese
    "economia","econômico","macroeconômico","pib","crescimento","recessão","desaceleração",
    "inflação","preços","custo de vida","índice de preços",
    "orçamento","fiscal","déficit","superávit","receita","imposto","subsídi",
    "dívida","calote","incumprimento","reestruturação","título","soberano",
    "taxa de juros","banco central","monetário",
    "moeda","câmbio","reservas","balança de pagamentos",
    "importação","exportação","comércio","tarifa","sanção",
    "banco","bancário","estabilidade financeira","liquidez",
    "desemprego","empregos","demissões",
]

PILLARS: Dict[str, List[str]] = {
    "InflationRisk": ["inflation","price hike","cost of living","shortage","scarcity","hausse des prix","pénurie","inflação","escassez"],
    "FXExternalRisk": ["exchange rate","currency","devaluation","forex","reserves","taux de change","dévaluation","câmbio","desvalorização"],
    "DebtFiscalRisk": ["debt","default","restructuring","bond","budget deficit","dette","défaut","reestruturação","dívida"],
    "FinancialSectorRisk": ["bank","liquidity","bank run","npl","insolvency","banque","liquidité","corrida bancária","insolvência"],
    "GrowthRealEconomyRisk": ["recession","slowdown","contraction","unemployment","layoffs","récession","chômage","recessão","desemprego"],
    "CommoditySupplyRisk": ["oil shock","fuel scarcity","supply disruption","logistics disruption","choc pétrolier","pénurie de carburant","escassez de combustível"],
    "PoliticalEconomyRisk": ["protest","unrest","coup","strike","sanction","manifestation","coup d'état","greve","golpe"],
    "ClimateDisasterRisk": ["drought","flood","cyclone","heatwave","crop failure","sécheresse","inondation","seca","inundação"],
}

SEVERITY_TIER_TERMS: Dict[int, List[str]] = {
    1: ["pressure","concern","moderate","slight","risk","uncertainty","pression","inquiétude","risque","incertitude","pressão","preocupação","risco","incerteza"],
    2: ["rising","worsening","strain","surge","spike","sharp increase","deterioration","hausse","aggravation","tension","détérioration","aumentando","piorando","deterioração"],
    3: ["crisis","collapse","severe","emergency","panic","distress","acute shortage","crise","effondrement","grave","urgence","panique","pénurie aiguë","crise","colapso","grave","emergência","pânico"],
    4: ["default","hyperinflation","bank run","sovereign default","meltdown","economic collapse","défaut","hyperinflation","panique bancaire","défaut souverain","calote","hiperinflação","corrida bancária"],
}

TITLE_RISK_HINTS = [
    "crisis","default","devaluation","inflation","shortage","collapse","debt","restructuring","recession","bank","emergency",
    "crise","défaut","dévaluation","inflation","pénurie","effondrement","dette","restructuration","récession","banque","urgence",
    "crise","calote","desvalorização","inflação","escassez","colapso","dívida","reestruturação","recessão","banco","emergência",
]


# =============================================================================
# 2) TEXT + REGEX
# =============================================================================
def fix_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    if _ftfy_fix_text is not None:
        return _ftfy_fix_text(s)
    return s

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def safe_lower(s: str) -> str:
    return (s or "").lower()

def compile_phrase_regex(terms: List[str]) -> re.Pattern:
    # Word boundary approach is good for Latin scripts; for Arabic etc. you’ll need a separate token strategy.
    escaped = []
    for t in terms:
        t = str(t).strip()
        if not t:
            continue
        t_esc = re.escape(t).replace(r"\ ", r"\s+")
        escaped.append(rf"\b{t_esc}\b")
    if not escaped:
        return re.compile(r"(?!x)x")
    return re.compile("|".join(escaped), flags=re.IGNORECASE)

RE_ECON = compile_phrase_regex(ECON_RELEVANCE_TERMS)
RE_TITLE_HINTS = compile_phrase_regex(TITLE_RISK_HINTS)
RE_PILLARS = {k: compile_phrase_regex(v) for k, v in PILLARS.items()}
RE_SEVERITY = {tier: compile_phrase_regex(terms) for tier, terms in SEVERITY_TIER_TERMS.items()}


# =============================================================================
# 3) PERIOD HELPERS
# =============================================================================
def ym_to_period(ym: str) -> pd.Period:
    return pd.Period(ym, freq="M")

def in_ym_range(ym: str, start_ym: Optional[str], end_ym: Optional[str]) -> bool:
    try:
        p = ym_to_period(ym)
    except Exception:
        return False
    if start_ym and p < ym_to_period(start_ym):
        return False
    if end_ym and p > ym_to_period(end_ym):
        return False
    return True

def derive_period_from_dt(dt: pd.Series, period: str) -> pd.Series:
    if period == "month":
        return dt.dt.to_period("M").astype(str)
    if period == "week":
        return dt.dt.to_period("W").astype(str)
    if period == "day":
        return dt.dt.date.astype(str)
    raise ValueError("period must be one of: month, week, day")


# =============================================================================
# 4) FILE DISCOVERY
# =============================================================================
def iter_article_files(
    root: Path,
    allowed_countries: Optional[Set[str]],
    start_ym: Optional[str],
    end_ym: Optional[str]
) -> Iterable[Tuple[str, str, str, Path]]:
    allowed = set(allowed_countries) if allowed_countries else None
    for country_dir in root.iterdir():
        if not country_dir.is_dir():
            continue
        country = country_dir.name
        if allowed is not None and country not in allowed:
            continue
        for site_dir in country_dir.iterdir():
            if not site_dir.is_dir():
                continue
            site = site_dir.name
            for month_dir in site_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                ym = month_dir.name
                if (start_ym or end_ym) and (not in_ym_range(ym, start_ym, end_ym)):
                    continue
                for f in month_dir.glob("articles_*.csv.gz"):
                    yield country, site, ym, f


def safe_read_articles_gz(fpath: Path, usecols: List[str]) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(
            fpath,
            compression="gzip",
            dtype=str,
            keep_default_na=False,
            usecols=usecols,
            encoding=ENCODING,
            encoding_errors="replace",
            on_bad_lines="error",
            low_memory=LOW_MEMORY_MODE
        )
    except (EOFError, OSError, gzip.BadGzipFile, EmptyDataError):
        return None
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if "title" not in df.columns or "text" not in df.columns:
        return None
    return df


# =============================================================================
# 5) SCORING (vectorized)
# =============================================================================
def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    title = df["title"].astype(str).map(fix_text).map(normalize_whitespace)
    text  = df["text"].astype(str).map(fix_text).map(normalize_whitespace)
    full  = (title + " " + text).map(safe_lower)

    relevance = full.str.contains(RE_ECON, regex=True).astype("int8")

    severity = pd.Series([0] * len(df), index=df.index, dtype="int16")
    rel_idx = relevance[relevance == 1].index
    if len(rel_idx) > 0:
        rel_text = full.loc[rel_idx]
        sev_val = pd.Series([1] * len(rel_idx), index=rel_idx, dtype="int16")
        for tier in sorted(RE_SEVERITY.keys()):
            hits = rel_text.str.contains(RE_SEVERITY[tier], regex=True)
            sev_val.loc[hits[hits].index] = tier
        severity.loc[rel_idx] = sev_val

    # -------------------------
    # Count mentions for diagnostics only; the original index uses article presence.
    # -------------------------
    pillar_counts = {}
    for p, rx in RE_PILLARS.items():
        pillar_counts[p] = full.str.count(rx.pattern).astype("int16")

    pillar_df = pd.DataFrame(pillar_counts, index=df.index)

    # number of distinct pillars active in article
    pillar_active_count = (pillar_df > 0).sum(axis=1).astype("int16")

    # total keyword mentions across all pillars
    pillar_total_mentions = pillar_df.sum(axis=1).astype("int16")

    conf = pd.Series([1.0] * len(df), index=df.index, dtype="float32")
    title_hit = title.map(safe_lower).str.contains(RE_TITLE_HINTS, regex=True)
    conf = conf + title_hit.astype("float32") * 0.5
    conf = conf + (text.str.len() >= 1200).astype("float32") * 0.2

    # Original confidence rule: multiple active pillars add 0.3, not a repetition bonus.
    conf = conf + (pillar_active_count >= 2).astype("float32") * 0.3
    conf = conf.clip(1.0, 2.0)

    article_score = relevance.astype("float32") * severity.astype("float32") * conf.astype("float32")

    out = pd.DataFrame({
        "relevance": relevance,
        "severity": severity,
        "confidence": conf,
        "article_score": article_score,
        "pillar_active_count": pillar_active_count,
        "pillar_total_mentions": pillar_total_mentions
    }, index=df.index)

    # A relevant article contributes once per pillar, regardless of repeated mentions.
    for p in PILLARS.keys():
        out[p] = pillar_df[p].gt(0).astype("int8")

    return out


# =============================================================================
# 6) PER-FILE WORKER (runs in separate process)
# =============================================================================
def process_one_file(args: Tuple[str, str, str, str, str, Optional[str]]) -> Dict[str, Any]:
    """
    Returns a dict:
      {
        "ok": bool,
        "skipped_reason": str | None,
        "file": str,
        "country": str,
        "agg": {(Country, Period): agg_dict, ...},
        "n_articles": int
      }
    """
    country, site, ym, fpath, period, date_col = args
    fpath = Path(fpath)

    usecols = ["title", "text"]
    if period in {"week", "day"} and date_col:
        usecols.append(date_col)

    df = safe_read_articles_gz(fpath, usecols=usecols)
    if df is None:
        return {"ok": False, "skipped_reason": "unreadable/empty/malformed", "file": str(fpath), "country": country, "agg": {}, "n_articles": 0}

    # period label
    if period == "month":
        df["Period"] = ym
    else:
        if date_col and date_col in df.columns:
            dt = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            df["Period"] = derive_period_from_dt(dt, period=period).fillna(ym)
        else:
            df["Period"] = ym

    scores = compute_scores(df)
    scores["Country"] = country
    scores["Period"] = df["Period"].values

    local_agg: Dict[Tuple[str, str], dict] = {}

    for (c, p), g in scores.groupby(["Country", "Period"], sort=False):
        key = (c, p)
        if key not in local_agg:
            local_agg[key] = {
                "n_articles": 0,
                "sum_article_score": 0.0,
                "n_relevant": 0,
                "sum_conf": 0.0,
                "sum_sev": 0.0,
                "sum_active_pillars": 0.0,
                "sum_total_pillar_mentions": 0.0,
                **{f"sum_{pill}": 0.0 for pill in PILLARS.keys()},
            }

        a = local_agg[key]
        a["n_articles"] += int(g.shape[0])
        a["sum_article_score"] += float(g["article_score"].sum())
        a["n_relevant"] += int(g["relevance"].sum())
        a["sum_conf"] += float(g["confidence"].sum())
        a["sum_sev"] += float(g["severity"].sum())
        a["sum_active_pillars"] += float(g["pillar_active_count"].sum())
        a["sum_total_pillar_mentions"] += float(g["pillar_total_mentions"].sum())

        for pill in PILLARS.keys():
            a[f"sum_{pill}"] += float((g["article_score"] * g[pill]).sum())

    return {"ok": True, "skipped_reason": None, "file": str(fpath), "country": country, "agg": local_agg, "n_articles": int(len(df))}


def merge_aggs(global_agg: Dict[Tuple[str, str], dict], local_agg: Dict[Tuple[str, str], dict]) -> None:
    for key, a in local_agg.items():
        if key not in global_agg:
            global_agg[key] = a
        else:
            g = global_agg[key]
            g["n_articles"] += a["n_articles"]
            g["sum_article_score"] += a["sum_article_score"]
            g["n_relevant"] += a["n_relevant"]
            g["sum_conf"] += a["sum_conf"]
            g["sum_sev"] += a["sum_sev"]
            g["sum_active_pillars"] += a["sum_active_pillars"]
            g["sum_total_pillar_mentions"] += a["sum_total_pillar_mentions"]
            for pill in PILLARS.keys():
                g[f"sum_{pill}"] += a[f"sum_{pill}"]


def finalize_agg(agg: Dict[Tuple[str, str], dict]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows_aeri, rows_pillars, rows_diag = [], [], []

    for (country, period_label), a in agg.items():
        n = a["n_articles"]
        if n <= 0:
            continue

        aeri = 100.0 * a["sum_article_score"] / n
        rows_aeri.append({"Country": country, "Period": period_label, "AERI": aeri})

        pr = {"Country": country, "Period": period_label}
        for pill in PILLARS.keys():
            pr[pill] = 100.0 * a[f"sum_{pill}"] / n
        rows_pillars.append(pr)

        avg_conf = a["sum_conf"] / n
        avg_sev = a["sum_sev"] / max(1, a["n_relevant"])
        avg_active_pillars = a["sum_active_pillars"] / n
        avg_pillar_mentions = a["sum_total_pillar_mentions"] / n

        rows_diag.append({
            "Country": country,
            "Period": period_label,
            "TotalArticles": n,
            "RelevantArticles": a["n_relevant"],
            "RelevantSharePct": 100.0 * a["n_relevant"] / n,
            "AvgConfidence": avg_conf,
            "AvgSeverityAmongRelevant": avg_sev,
            "AvgActivePillarsPerArticle": avg_active_pillars,
            "AvgPillarMentionsPerArticle": avg_pillar_mentions
        })

    df_aeri = pd.DataFrame(rows_aeri).sort_values(["Country", "Period"])
    df_pillars = pd.DataFrame(rows_pillars).sort_values(["Country", "Period"])
    df_diag = pd.DataFrame(rows_diag).sort_values(["Country", "Period"])
    return df_aeri, df_pillars, df_diag


# =============================================================================
# 7) PROMPTING
# =============================================================================
def list_available_countries(root: Path) -> List[str]:
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])

def prompt_setup(root: Path) -> Tuple[Optional[Set[str]], Optional[str], Optional[str], str, Optional[str]]:
    available = list_available_countries(root)
    print(f"\nAvailable countries ({len(available)}):")
    print(", ".join(available) if available else "(none found)")

    s = input("\nEnter selected countries (comma-separated), or leave empty for ALL: ").strip()
    if s:
        selected_list = [x.strip() for x in s.split(",") if x.strip()]
        selected = {c for c in selected_list if c in set(available)}
        missing = sorted(set(selected_list) - set(selected))
        if missing:
            print(f"⚠️ Ignored (not found): {missing}")
        if not selected:
            print("⚠️ No valid countries selected; defaulting to ALL.")
            selected = None
    else:
        selected = None

    start_ym = input("Enter START year-month (YYYY-MM) or leave empty: ").strip() or None
    end_ym   = input("Enter END year-month (YYYY-MM) or leave empty: ").strip() or None

    period = input(f"Aggregation period (month/week/day) [{DEFAULT_PERIOD}]: ").strip().lower() or DEFAULT_PERIOD
    if period not in {"month", "week", "day"}:
        print("Invalid period; using default:", DEFAULT_PERIOD)
        period = DEFAULT_PERIOD

    date_col = input(f"Optional date column name (press Enter if none) [{DEFAULT_DATE_COL}]: ").strip()
    if date_col == "":
        date_col = DEFAULT_DATE_COL

    return selected, start_ym, end_ym, period, date_col


# =============================================================================
# 8) MAIN RUN (parallel)
# =============================================================================
def run_aeri_parallel(
    root: Path,
    out_dir: Path,
    period: str,
    date_col: Optional[str],
    selected_countries: Optional[Set[str]],
    start_ym: Optional[str],
    end_ym: Optional[str]
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list(iter_article_files(root, selected_countries, start_ym, end_ym))
    if not files:
        print("❌ No files matched your filters. Check country names and YYYY-MM range.")
        return

    tasks = [(c, s, ym, str(fp), period, date_col) for (c, s, ym, fp) in files]

    workers = MAX_WORKERS
    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 1)

    print(f"\n✅ Matched files: {len(tasks):,}")
    print(f"✅ Using workers: {workers}")
    print("✅ Computing AERI...")

    global_agg: Dict[Tuple[str, str], dict] = {}
    skipped = []
    scanned = 0
    ok_files = 0
    unreadable = 0
    articles_total = 0

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(process_one_file, t) for t in tasks]

        for fut in as_completed(futures):
            res = fut.result()
            scanned += 1

            if not res["ok"]:
                unreadable += 1
                skipped.append({"file": res["file"], "country": res["country"], "reason": res["skipped_reason"]})
            else:
                ok_files += 1
                articles_total += res["n_articles"]
                merge_aggs(global_agg, res["agg"])

            if PROGRESS_EVERY_N_FILES and scanned % PROGRESS_EVERY_N_FILES == 0:
                print(f"scanned files: {scanned:,} | ok: {ok_files:,} | unreadable: {unreadable:,} | articles so far: {articles_total:,}")

    if skipped:
        skipped_path = out_dir / "skipped_article_files.csv"
        pd.DataFrame(skipped).to_csv(skipped_path, index=False, encoding="utf-8")
        print(f"\n⚠️ Skipped {len(skipped):,} file(s). Log: {skipped_path}")

    df_aeri, df_pillars, df_diag = finalize_agg(global_agg)

    aeri_path = out_dir / "aeri_country_period.csv"
    pillars_path = out_dir / "aeri_pillars_country_period.csv"
    diag_path = out_dir / "aeri_diagnostics.csv"

    df_aeri.to_csv(aeri_path, index=False, encoding="utf-8")
    df_pillars.to_csv(pillars_path, index=False, encoding="utf-8")
    df_diag.to_csv(diag_path, index=False, encoding="utf-8")

    print("\n✅ DONE")
    print(f"✅ Files scanned:     {scanned:,}")
    print(f"✅ Files ok:          {ok_files:,}")
    print(f"✅ Files unreadable:  {unreadable:,}")
    print(f"✅ Articles processed:{articles_total:,}")
    print(f"✅ Saved AERI:        {aeri_path}")
    print(f"✅ Saved Pillars:     {pillars_path}")
    print(f"✅ Saved Diagnostics: {diag_path}")


def main():
    # Direct execution now uses the history-preserving complete workflow.
    from run_aeri import main as run_pipeline
    run_pipeline()

if __name__ == "__main__":
    main()
