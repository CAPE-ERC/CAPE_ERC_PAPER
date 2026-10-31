"""Exact normalized-body deduplication using frozen archived aggregates.

The archive is never modified. Within each country-month, one representative of
each normalized body (NFKC, casefold, whitespace collapse; >=200 characters) is
retained. Only removed copies are rescored: their contributions are subtracted
from the archived raw numerator and diagnostics. This is algebraically identical
to rescoring all rows when the archive reconciles to the frozen aggregate.
"""
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,as_completed
import pandas as pd,numpy as np,json,hashlib,unicodedata,re,heapq,math,platform
import frozen_scoring as frozen
import fast_frozen_scores as fast
HERE=Path(__file__).resolve().parent;OUT=HERE/'exact_raw_dedup';OUT.mkdir(exist_ok=True)
P=list(frozen.PILLARS);SEED=20260910;WS=re.compile(r'\s+')
def norm(x):return WS.sub(' ',unicodedata.normalize('NFKC',str(x)).casefold()).strip()
def sha(x):return hashlib.sha256(x.encode('utf-8')).hexdigest()
def u(key):return (int(sha(str(SEED)+'|'+key)[:16],16)+1)/(2**64+1)
def keep(heap,priority,item,n):
 e=(-priority,item['id'],item)
 if len(heap)<n:heapq.heappush(heap,e)
 elif e>heap[0]:heapq.heapreplace(heap,e)
def read(f):
 try:
  raw=Path(f['path']).read_bytes();import io
  d=pd.read_csv(io.BytesIO(raw),compression='gzip',dtype=str,keep_default_na=False,usecols=lambda c:c in {'title','text','url'},encoding='utf-8',encoding_errors='replace',on_bad_lines='error')
  if not {'title','text'}<=set(d):raise ValueError('missing title/text')
  d['url']=d['url'] if 'url' in d else '';d['site']=f['site'];d['source_file']=f['path'];d['source_row']=np.arange(len(d))+2
  return d,dict(path=f['path'],sha256=hashlib.sha256(raw).hexdigest(),rows=len(d)),None
 except Exception as e:return None,None,dict(path=f['path'],error=str(e))
def run_country(args):
 country,files,base=args;dest=OUT/(country+'.json')
 if dest.exists():return country,'cached'
 months=defaultdict(list)
 for f in files:months[f['month']].append(f)
 random_pool=[];challenge_pool=[];rows=[];errors=[];manifest=[];links=[];examples=[];national=set()
 high=float(base.AERI.quantile(.9));rare=list(base[P].mean().nsmallest(2).index)
 for month,fs in sorted(months.items()):
  parts=[]
  with ThreadPoolExecutor(max_workers=12) as pool:
   for d,m,e in pool.map(read,sorted(fs,key=lambda z:z['path'])):
    if e:errors.append(e)
    else:parts.append(d);manifest.append(m)
  if not parts:continue
  d=pd.concat(parts,ignore_index=True).fillna('');n=len(d);body=d.text.astype(str);eligible=body.str.len().ge(200);dup=eligible & body.duplicated(keep='first');removed=np.flatnonzero(dup.to_numpy()).tolist();unique=np.flatnonzero((~dup).to_numpy()).tolist()
  # Stable 64-bit content fingerprints select small candidate pools in vectorized code.
  content=(d.title.astype(str)+'\x00'+body).iloc[unique];finger=pd.util.hash_pandas_object(content,index=False).to_numpy(dtype='uint64');fresh=[]
  for pos,hv in zip(unique,finger):
   key=int(hv)
   if key not in national:national.add(key);fresh.append(pos)
  if fresh:
   cand=d.iloc[fresh].copy();hv=pd.util.hash_pandas_object(cand.title.astype(str)+'\x00'+cand.text.astype(str),index=False).to_numpy(dtype='uint64');order=np.argsort(hv)[:min(30,len(cand))]
   is_high=len(base.loc[base.Period==month]) and float(base.loc[base.Period==month,'AERI'].iloc[0])>=high
   for pos in order:
    r=cand.iloc[int(pos)];key=sha(str(r.title)+'\x00'+str(r.text));ident=sha(country+'|'+key)[:20];item=dict(id=ident,body_sha256=key,country=country,month=month,site=r.site,source_file=r.source_file,source_row=int(r.source_row),title=r.title,text=r.text,url=r.url)
    keep(random_pool,u(country+'|random|'+key),item,180);keep(challenge_pool,-math.log(u(country+'|challenge-pool|'+key))/(5 if is_high else 1),item,1200)
  cross_removed=0
  if removed:
   reps=d.loc[eligible].drop_duplicates('text',keep='first').set_index('text')
   for i in removed[:40-len(examples)]:
    r=d.iloc[i];rep=reps.loc[r.text];examples.append(dict(country=country,month=month,representative_title=rep.title,duplicate_title=r.title,representative_file=rep.source_file,duplicate_file=r.source_file))
   rep_sites=reps.site.reindex(d.loc[removed,'text']).to_numpy();cross_removed=int((rep_sites!=d.loc[removed,'site'].to_numpy()).sum())
  b=base[base.Period==month]
  if len(b)!=1:continue
  b=b.iloc[0]
  base_n=int(b.TotalArticles)
  if n!=base_n:
   errors.append(dict(path=country+'/'+month,error=f'archive count {n} != frozen aggregate {base_n}; unmatched frozen records retained in denominator'))
  sd=fast.compute_scores(d.iloc[removed].reset_index(drop=True)) if removed else pd.DataFrame(columns=fast.COLUMNS)
  rn=base_n-len(removed);rel=int(b.RelevantArticles)-int(sd.relevance.sum());sevsum=float(b.AvgSeverityAmongRelevant)*int(b.RelevantArticles)-float(sd.severity.sum())
  row=dict(Country=country,Period=month,raw_n=base_n,archive_observed_n=n,exact_n=rn,removed=len(removed),raw_AERI=float(b.AERI),exact_AERI=(float(b.AERI)*base_n/100-float(sd.article_score.sum()))*100/rn,raw_relevant=int(b.RelevantArticles),exact_relevant=rel,raw_severity=float(b.AvgSeverityAmongRelevant),exact_severity=sevsum/rel if rel else 0,cross_outlet_removed=cross_removed)
  for p in P:row['raw_'+p]=float(b[p]);row['exact_'+p]=(float(b[p])*base_n/100-float((sd.article_score.astype(float)*sd[p]).sum()))*100/rn
  rows.append(row)
 # Score reserved challenge pool only, then priority-sample with severity/rare/difficulty.
 cp=[e[2] for e in sorted(challenge_pool,reverse=True)]
 if cp:
  sc=fast.compute_scores(pd.DataFrame({'title':[x['title'] for x in cp],'text':[x['text'] for x in cp]}))
  ranked=[]
  for item,score in zip(cp,sc.itertuples(index=False)):
   item.update(relevance=int(score.relevance),severity=int(score.severity),**{p:int(getattr(score,p)) for p in P})
   w=1+4*int(item['month'] in set(base.loc[base.AERI>=high,'Period']))+2*int(score.severity>=3)+2*int(any(getattr(score,p) for p in rare))+2*int((score.relevance==0 and sum(getattr(score,p) for p in P)>0) or (score.relevance==1 and score.severity==1))
   ranked.append((-math.log(u(country+'|challenge-final|'+item['body_sha256']))/w,item))
  ranked.sort(key=lambda x:x[0])
 else:ranked=[]
 payload=dict(country=country,rows=rows,errors=errors,manifest=manifest,links=links,examples=examples,frame_size=len(national),random_candidates=[e[2] for e in sorted(random_pool,reverse=True)],challenge_candidates=[x[1] for x in ranked[:180]])
 dest.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');return country,dict(months=len(rows),errors=len(errors),frame=len(national))
if __name__=='__main__':
 print('Loading inventory...',flush=True)
 inv=json.loads((HERE/'corpus_inventory.json').read_text());base=pd.read_csv(HERE.parent/'sources/aeri_model_comparison.csv');base=base[base.Period.between('2015-01','2025-12')]
 print('Grouping files...',flush=True)
 groups=defaultdict(list)
 valid_countries=set(base.Country)
 for f in inv:
  if f['country'] in valid_countries:groups[f['country']].append(f)
 print('Starting workers...',flush=True)
 prov=dict(seed=SEED,method='exact decoded article body within country-month; >=200 characters',scorer_sha256=hashlib.sha256((HERE/'frozen_scoring.py').read_bytes()).hexdigest(),fast_scorer_equivalence=json.loads((HERE/'fast_scoring_equivalence_test.json').read_text()),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inventory_sha256=hashlib.sha256((HERE/'corpus_inventory.json').read_bytes()).hexdigest(),python=platform.python_version(),pandas=pd.__version__)
 (OUT/'run_provenance.json').write_text(json.dumps(prov,indent=2))
 with ProcessPoolExecutor(max_workers=6) as pool:
  jobs=[pool.submit(run_country,(c,groups[c],base[base.Country==c])) for c in sorted(base.Country.unique())]
  for j in as_completed(jobs):print('DONE',j.result(),flush=True)
