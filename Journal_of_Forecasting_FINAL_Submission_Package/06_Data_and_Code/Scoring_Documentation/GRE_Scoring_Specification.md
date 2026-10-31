# Frozen GRE article-level scoring specification

This file documents the exact article-level production rule used to construct the frozen Growth/Real Economy (GRE) signal supplied with the forecasting replication package. It is a reproducibility record of the baseline measurement architecture, not an alternative-scoring robustness exercise.

- Production method identifier: `original_article_presence_v1`
- Verified production-source snapshot SHA-256: `58cb3d9921cee89a3fb6ec209312614dcca88031c2fdefbbad4cd36da7133915`
- Text is passed through `ftfy.fix_text` when that optional dependency is available, then whitespace is normalized. Matching is case-insensitive. Multi-word phrases permit normalized whitespace between words. Headline and body text are combined for economic relevance, severity, and domain activation.

## 1. Economic-relevance lexicon

An article receives `R_i = 1` when its normalized headline-plus-body text matches at least one of the following frozen terms:

```text
economy, economic, macroeconomic, gdp, growth, recession, slowdown, inflation, prices, cost of living, consumer prices, cpi, budget, fiscal, deficit, surplus, revenue, tax, subsidy, debt, default, restructuring, bond, treasury, sovereign, interest rate, policy rate, central bank, monetary, currency, exchange rate, forex, reserves, balance of payments, import, export, trade, tariff, sanction, bank, banking, financial stability, liquidity, capital adequacy, npl, unemployment, jobs, layoffs, wages, imf, world bank, afdb, économie, economique, macroéconomie, pib, croissance, récession, ralentissement, inflation, prix, coût de la vie, indice des prix, budget, fiscal, déficit, excédent, recettes, impôt, taxe, subvention, dette, défaut, restructuration, obligation, souverain, taux d'intérêt, banque centrale, monétaire, monnaie, taux de change, réserves, balance des paiements, importation, exportation, commerce, tarif, sanction, banque, bancaire, stabilité financière, liquidité, chômage, emplois, licenciements, economia, econômico, macroeconômico, pib, crescimento, recessão, desaceleração, inflação, preços, custo de vida, índice de preços, orçamento, fiscal, déficit, superávit, receita, imposto, subsídi, dívida, calote, incumprimento, reestruturação, título, soberano, taxa de juros, banco central, monetário, moeda, câmbio, reservas, balança de pagamentos, importação, exportação, comércio, tarifa, sanção, banco, bancário, estabilidade financeira, liquidez, desemprego, empregos, demissões
```

## 2. Domain dictionaries

Domain tags are non-exclusive. Repeated matches inside the same article do not multiply that domain contribution. The multi-domain indicator used in the emphasis weight depends on the number of distinct active domains, so all eight frozen dictionaries are listed here.

### InflationRisk

```text
inflation, price hike, cost of living, shortage, scarcity, hausse des prix, pénurie, inflação, escassez
```

### FXExternalRisk

```text
exchange rate, currency, devaluation, forex, reserves, taux de change, dévaluation, câmbio, desvalorização
```

### DebtFiscalRisk

```text
debt, default, restructuring, bond, budget deficit, dette, défaut, reestruturação, dívida
```

### FinancialSectorRisk

```text
bank, liquidity, bank run, npl, insolvency, banque, liquidité, corrida bancária, insolvência
```

### GrowthRealEconomyRisk

```text
recession, slowdown, contraction, unemployment, layoffs, récession, chômage, recessão, desemprego
```

### CommoditySupplyRisk

```text
oil shock, fuel scarcity, supply disruption, logistics disruption, choc pétrolier, pénurie de carburant, escassez de combustível
```

### PoliticalEconomyRisk

```text
protest, unrest, coup, strike, sanction, manifestation, coup d'état, greve, golpe
```

### ClimateDisasterRisk

```text
drought, flood, cyclone, heatwave, crop failure, sécheresse, inondation, seca, inundação
```

## 3. Severity mapping

Economic-relevance matches receive a baseline severity of 1. If severity terms are present, the highest matched tier is used. Non-relevant articles receive severity 0.

### Tier 1

```text
pressure, concern, moderate, slight, risk, uncertainty, pression, inquiétude, risque, incertitude, pressão, preocupação, risco, incerteza
```

### Tier 2

```text
rising, worsening, strain, surge, spike, sharp increase, deterioration, hausse, aggravation, tension, détérioration, aumentando, piorando, deterioração
```

### Tier 3

```text
crisis, collapse, severe, emergency, panic, distress, acute shortage, crise, effondrement, grave, urgence, panique, pénurie aiguë, crise, colapso, grave, emergência, pânico
```

### Tier 4

```text
default, hyperinflation, bank run, sovereign default, meltdown, economic collapse, défaut, hyperinflation, panique bancaire, défaut souverain, calote, hiperinflação, corrida bancária
```

## 4. Headline cues used in the emphasis weight

The headline indicator `T_i` equals one when the normalized title matches at least one of these frozen title-risk cues:

```text
crisis, default, devaluation, inflation, shortage, collapse, debt, restructuring, recession, bank, emergency, crise, défaut, dévaluation, inflation, pénurie, effondrement, dette, restructuration, récession, banque, urgence, crise, calote, desvalorização, inflação, escassez, colapso, dívida, reestruturação, recessão, banco, emergência
```

## 5. Emphasis rule and article contribution

- `T_i = 1` when a title cue is present.
- `L_i = 1` when the normalized article body contains at least 1,200 characters.
- `M_i = 1` when at least two distinct domain dictionaries are active in the article.
- `W_i = clip(1 + 0.5 T_i + 0.2 L_i + 0.3 M_i, 1, 2)`.
- `G_i = 1` when `GrowthRealEconomyRisk` is active.
- `Q_i = R_i * G_i * S_i * W_i`.
- A qualifying article contributes at most once to the GRE domain, regardless of repeated keyword occurrences. Keyword occurrence counts are diagnostics only.

## 6. Country-month aggregation

For retained article set `A_ct` and total retained article count `N_ct`:

```text
GRE_ct = (100 / N_ct) * sum_i Q_i
```

The denominator includes every retained article record in the country-month, including records with zero GRE contribution.

## 7. Scope of robustness claims

The forecasting paper keeps this article-level scoring architecture fixed. Corpus and signal-level checks cover exact-text duplication, article-volume thresholds, monotone transformations, upper-tail caps, temporal-disaggregation choices, forecast-model alternatives, dependence, and resampling. The paper does **not** claim that the forecast result is invariant to alternative article-level dictionaries, severity maps, or emphasis coefficients. The article-level contribution of this documentation is exact baseline transparency and reproducibility.
