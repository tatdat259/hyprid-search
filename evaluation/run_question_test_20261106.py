import json, urllib.request, urllib.error, time
from pathlib import Path

base='http://127.0.0.1:8000'
qs=[
(1,"What was Apple's Services revenue in fiscal year 2024?",['AAPL'],['10-K'],'answerable',['services','revenue','2024']),
(2,"Summarize NVIDIA's disclosed supply-chain risks.",['NVDA'],['10-K'],'answerable',['supply','risk']),
(3,"What was Microsoft's cloud revenue growth in fiscal year 2024?",['MSFT'],['10-K'],'answerable',['cloud','revenue','2024']),
(4,"What battery supply-chain risks does Tesla disclose?",['TSLA'],['10-K'],'answerable',['battery','supply','risk']),
(5,"What fiscal year does NVIDIA's latest 10-K cover, and when was it filed?",['NVDA'],['10-K'],'answerable',['2024','2025']),
(6,"What was Apple's revenue in fiscal year 2023, and when was that report filed?",['AAPL'],['10-K'],'answerable',['revenue','2023','2024']),
(7,"Compare Microsoft's revenue by segment between FY2023 and FY2024.",['MSFT'],['10-K'],'answerable',['revenue','2023','2024']),
(8,"What were NVIDIA's revenue by segment for fiscal 2024 and fiscal 2023?",['NVDA'],['10-K'],'answerable',['revenue','2024','2023']),
(9,"What was Tesla's revenue by geographic region in its latest fiscal year?",['TSLA'],['10-K'],'answerable',['revenue','region']),
(10,"What was VinFast's revenue in fiscal year 2024?",['AAPL'],['10-K'],'insufficient_context',['vinfast']),
(11,"What was Apple's revenue in fiscal year 2019?",['AAPL'],['10-K'],'insufficient_context',['2019']),
(12,"Does Tesla operate in Vietnam?",['TSLA'],['10-K'],'insufficient_context',['vietnam']),
(13,"Calculate the combined revenue of Apple and Microsoft in FY2024.",['AAPL','MSFT'],['10-K'],'answerable',['revenue','2024']),
(14,"What is Apple's revenue growth rate from FY2023 to FY2024?",['AAPL'],['10-K'],'answerable',['revenue','2023','2024']),
(15,"Calculate NVIDIA's gross margin in FY2024.",['NVDA'],['10-K'],'insufficient_context',['gross margin','2024']),
(16,"Summarize NVIDIA's disclosed risks.",['NVDA'],['10-K'],'answerable',['risk']),
(17,"What risks does NVIDIA disclose about supply chain?",['NVDA'],['10-K'],'answerable',['risk','supply']),
]

def call(payload):
    data=json.dumps(payload).encode()
    req=urllib.request.Request(base+'/api/search',data=data,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=60) as r: return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e: return None, {'error':str(e)}

rows=[]
for no,q,tickers,forms,expected,terms in qs:
    status,body=call({'query':q,'method':'rerank','k':10,'tickers':tickers,'form_types':forms})
    results=body.get('results',[]) if isinstance(body,dict) else []
    joined=' '.join((r.get('full_text') or r.get('excerpt') or '').lower() for r in results)
    hits=[term for term in terms if term.lower() in joined]
    # Conservative retrieval evidence score: answerable requires >=2 requested signals; insufficient_context requires no strong matching answer signal.
    if expected=='answerable':
        passed=len(hits)>=min(2,len(terms)) and len(results)>0
    else:
        passed=(len(results)==0) if no==10 else (len(hits)==0 or len(results)==0)
    top=[]
    for r in results[:3]: top.append({'rank':r.get('rank'),'ticker':r.get('ticker'),'fiscal_year':r.get('fiscal_year'),'section':r.get('section_title'),'excerpt':r.get('excerpt','')[:300]})
    rows.append({'id':no,'query':q,'expected_class':expected,'http_status':status,'result_count':len(results),'term_hits':hits,'retrieval_pass':bool(passed),'top3':top,'error':body.get('error') if isinstance(body,dict) else None})

summary={'total':len(rows),'retrieval_passed':sum(r['retrieval_pass'] for r in rows),'retrieval_accuracy':sum(r['retrieval_pass'] for r in rows)/len(rows),'rows':rows,'note':'This is evidence/retrieval scoring, not end-to-end generated-answer scoring. /api/ask returned generation_invalid_output in live smoke test.'}
out=Path('evaluation/ask_question_test_20261106.json'); out.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
md=Path('evaluation/ask_question_test_20261106.md')
lines=['# Generated Question Test Report','',f"- Total questions: {summary['total']}",f"- Evidence/retrieval passed: {summary['retrieval_passed']}/{summary['total']} ({summary['retrieval_accuracy']:.1%})",'- Scope: `/api/search` with `method=rerank`, `k=10`, and the filters from the question file.','- End-to-end `/api/ask` generation was not counted because the live provider returned `generation_invalid_output`.','', '| # | Expected class | Results | Term signals | Retrieval pass |', '|---:|---|---:|---|:---:|']
for r in rows: lines.append(f"| {r['id']} | {r['expected_class']} | {r['result_count']} | {', '.join(r['term_hits']) or '—'} | {'✅' if r['retrieval_pass'] else '❌'} |")
md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'output_json':str(out.resolve()),'output_md':str(md.resolve()),'passed':summary['retrieval_passed'],'total':summary['total']},ensure_ascii=False))
