"""Single-pass matcher equivalent to the frozen relevance/severity/pillar rules.

Overlapping lookahead preserves phrases starting inside another phrase. Nested
matches are precomputed from frozen regexes. Unused mention-count diagnostics
are deliberately omitted; every field used in AERI, ARS and audit sampling is
checked against frozen_scoring.compute_scores in test_fast_scores.py.
"""
import re
import numpy as np,pandas as pd
import frozen_scoring as s
P=list(s.PILLARS)
COLUMNS=['relevance','severity','confidence','article_score','pillar_active_count']+P
terms=list(dict.fromkeys(s.ECON_RELEVANCE_TERMS+s.TITLE_RISK_HINTS+sum(s.PILLARS.values(),[])+sum(s.SEVERITY_TIER_TERMS.values(),[])))
trie={}
for term in terms:
 node=trie
 for ch in term:node=node.setdefault(ch,{})
 node[None]={}
def emit(node):
 options=[(r'\s+' if ch==' ' else re.escape(ch))+emit(child) for ch,child in node.items() if ch is not None]
 if None in node:options.append('')
 return options[0] if len(options)==1 else '(?:'+'|'.join(options)+')'
RX=re.compile(r'(?=(\b'+emit(trie)+r'\b))',re.IGNORECASE)
def features(t):return (int(bool(s.RE_ECON.search(t))),max([0]+[k for k,rx in s.RE_SEVERITY.items() if rx.search(t)]),sum((1<<i) for i,p in enumerate(P) if s.RE_PILLARS[p].search(t)))
FEATURES={t:features(t) for t in terms}
def compute_scores(df):
 rows=[]
 for title,text in zip(df.title,df.text):
  title=s.normalize_whitespace(s.fix_text(title));text=s.normalize_whitespace(s.fix_text(text));full=(title+' '+text).lower()
  relevant=0;tier=0;bits=0
  for m in RX.finditer(full):
   phrase=m.group(1);f=FEATURES.get(phrase)
   if f is None:f=features(phrase);FEATURES[phrase]=f
   relevant|=f[0];tier=max(tier,f[1]);bits|=f[2]
  severity=max(1,tier) if relevant else 0
  flags=[int(bool(bits&(1<<i))) for i in range(8)];active=sum(flags)
  conf=np.float32(1)
  conf=np.float32(conf+np.float32(bool(s.RE_TITLE_HINTS.search(title.lower())))*np.float32(.5))
  conf=np.float32(conf+np.float32(len(text)>=1200)*np.float32(.2))
  conf=np.float32(conf+np.float32(active>=2)*np.float32(.3));conf=np.clip(conf,np.float32(1),np.float32(2))
  score=np.float32(np.float32(relevant)*np.float32(severity)*conf)
  rows.append([relevant,severity,conf,score,active]+flags)
 return pd.DataFrame(rows,columns=COLUMNS,index=df.index)
