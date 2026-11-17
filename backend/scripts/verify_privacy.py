"""差分隐私发布验证：多周贡献敏感度、并发争抢不超支、扣费中断重试一致、共享最小化。
运行：docker compose exec -T backend python -m scripts.verify_privacy
全程在一次性测试库 cohort_dp_verify 上执行，结束即删除，不触碰业务库与真实预算。"""
import os,sys,json,threading
from urllib.parse import urlsplit,urlunsplit
from decimal import Decimal
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker
from src.config.database import Base
from src.models.entities import Cohort,Release,PrivacyBudget
from src.schemas.business import ReleaseInput
from src.services.privacy import sensitivity,laplace,true_vector,build_result,charge,process_release,create_release,shared_view,dump_release,budget_view
CHECKS=[]
def check(name,cond,detail=''):
 CHECKS.append((name,bool(cond)));print(('PASS' if cond else 'FAIL'),name,detail)
def keys(obj,found):
 if isinstance(obj,dict):
  for k,v in obj.items():found.add(k);keys(v,found)
 elif isinstance(obj,list):
  for v in obj:keys(v,found)
 return found
url=os.environ['DATABASE_URL'];p=urlsplit(url)
netloc='root:'+p.password+'@'+p.hostname+((':'+str(p.port)) if p.port else '')
server=urlunsplit((p.scheme,netloc,'','',''));testdb=urlunsplit((p.scheme,netloc,'/cohort_dp_verify','',''))
admin=create_engine(server)
with admin.connect() as c:
 c.execution_options(isolation_level='AUTOCOMMIT').execute(text('DROP DATABASE IF EXISTS cohort_dp_verify'))
 c.execution_options(isolation_level='AUTOCOMMIT').execute(text('CREATE DATABASE cohort_dp_verify'))
engine=create_engine(testdb);Base.metadata.create_all(engine);T=sessionmaker(bind=engine,expire_on_commit=False)
def ev(learner,day):return {'code':learner+'-'+day,'learner':learner,'occurred_at':day+'T09:00:00+08:00','course':'数据素养','note':''}
events=[]
for i in range(1,21):
 events.append(ev(f'CQ-A{i:02}','2026-10-06'))
 if i<=10:events.append(ev(f'CQ-A{i:02}','2026-10-13'))
for i in range(1,16):events.append(ev(f'CQ-B{i:02}','2026-10-14'))
for day in ('2026-10-05','2026-10-12','2026-10-19','2026-10-26'):events.append(ev('CQ-HEAVY',day))#同一工号横跨4个成熟周
snapshot={'config':{'name':'验证方案','start_week':'2026-10-05','end_week':'2026-10-12','as_of':'2026-11-01','horizon':3},'events':events}
try:
 with T() as s:s.add(PrivacyBudget(id=1,total=Decimal('1'),spent=Decimal('0')));s.commit()
 with T() as s:
  s.add(Cohort(name='验证方案',start_week='2026-10-05',end_week='2026-10-12',as_of='2026-11-01',horizon=3,state='done',result={'snapshot':snapshot}));s.commit();cid=s.query(Cohort).first().id
 # 1. 多周贡献：同一工号可影响多个周计数，整表L1敏感度=horizon+2
 base=true_vector(snapshot)
 check('真实计数口径',base==[21,21,11,1,1,15,15,0,0],str(base))
 learners=sorted({e['learner'] for e in events});deltas={}
 for learner in learners:
  adj={'config':snapshot['config'],'events':[e for e in events if e['learner']!=learner]}
  deltas[learner]=sum(abs(a-b) for a,b in zip(base,true_vector(adj)))
 check('多周贡献上界 Δ=horizon+2',sensitivity(3)==5 and max(deltas.values())<=sensitivity(3),'max='+str(max(deltas.values())))
 check('重度学员贡献恰为Δ（界限紧致）',deltas['CQ-HEAVY']==5,'delta='+str(deltas['CQ-HEAVY']))
 seed=bytes.fromhex('ab'*32);samples=[laplace(seed,f'k{i}',2.5) for i in range(60000)]
 mean=sum(samples)/len(samples);var=sum((x-mean)**2 for x in samples)/len(samples)
 check('Laplace噪声均值≈0',abs(mean)<0.05,f'mean={mean:.4f}')
 check('Laplace噪声方差≈2b²',abs(var-12.5)/12.5<0.15,f'var={var:.3f}')
 check('同种子同标签噪声确定',laplace(seed,'x',1.0)==laplace(seed,'x',1.0) and laplace(seed,'x',1.0)!=laplace(seed,'y',1.0))
 # 2. 预算生命周期：自选消耗、超额拒绝、撤回不返还、幂等提交
 with T() as s:
  data=ReleaseInput(cohort_id=cid,name='生命周期发布',epsilon=Decimal('0.4'),request_id='verify-life-0001')
  r,new=create_release(s,data,'tester');rid=r.id
  again=ReleaseInput(cohort_id=cid,name='生命周期发布',epsilon=Decimal('0.4'),request_id='verify-life-0001')
  r2,new2=create_release(s,again,'tester')
 check('同request_id幂等（不重复建单）',new and not new2 and r2.id==rid)
 with T() as s: outcome=process_release(s,rid)
 with T() as s:
  b=budget_view(s);r=s.get(Release,rid)
 check('发布生效且预算同步扣减',outcome=='published' and r.state=='published' and abs(b['spent']-0.4)<1e-9 and abs(b['remaining']-0.6)<1e-9,str(b))
 with T() as s:
  big=ReleaseInput(cohort_id=cid,name='超额发布',epsilon=Decimal('0.7'),request_id='verify-life-0002')
  try:create_release(s,big,'tester');over='created'
  except Exception as e:over=getattr(e,'status_code',None)
 check('提交侧超额拒绝(409)',over==409)
 with T() as s:
  r60,_=create_release(s,ReleaseInput(cohort_id=cid,name='竞态发布A',epsilon=Decimal('0.6'),request_id='verify-life-0003'),'tester');rid60=r60.id
  r50,_=create_release(s,ReleaseInput(cohort_id=cid,name='竞态发布B',epsilon=Decimal('0.5'),request_id='verify-life-0004'),'tester');rid50=r50.id
  o1=process_release(s,rid60);o2=process_release(s,rid50);b=budget_view(s)
 check('处理侧超额拒绝且不扣费',o1=='published' and o2=='rejected' and abs(b['spent']-1.0)<1e-9,f'{o1}/{o2} spent={b["spent"]}')
 with T() as s:
  r=s.get(Release,rid);r.state='withdrawn';s.commit()
 with T() as s:b=budget_view(s)
 check('撤回不返还预算',abs(b['spent']-1.0)<1e-9,str(b))
 # 3. 并发争抢：5×0.25 对总量1，恰4过1拒，绝不超支
 for round_ in range(3):
  with T() as s:s.execute(text('UPDATE privacy_budget SET spent=0 WHERE id=1'));s.commit()
  ids=[]
  with T() as s:
   for k in range(5):
    r,_=create_release(s,ReleaseInput(cohort_id=cid,name=f'并发R{round_}-{k}',epsilon=Decimal('0.25'),request_id=f'verify-race-{round_}-{k}'),'tester');ids.append(r.id)
  outcomes=[];barrier=threading.Barrier(5)
  def work(i):
   barrier.wait()
   with T() as s:outcomes.append(process_release(s,i))
  threads=[threading.Thread(target=work,args=(i,)) for i in ids]
  for t in threads:t.start()
  for t in threads:t.join()
  with T() as s:b=budget_view(s)
  check(f'并发争抢第{round_+1}轮：4过1拒不超支',sorted(outcomes)==['published']*4+['rejected'] and abs(b['spent']-1.0)<1e-9,f'{sorted(outcomes)} spent={b["spent"]}')
 # 4. 扣费中断：中断回滚→重试一致；提交后重试→不重抽噪声、不重复扣费
 with T() as s:
  s.execute(text('UPDATE privacy_budget SET spent=0 WHERE id=1'))
  r,_=create_release(s,ReleaseInput(cohort_id=cid,name='中断发布',epsilon=Decimal('0.4'),request_id='verify-crash-0001'),'tester');crid=r.id
 s1=T();r1=s1.get(Release,crid);charged=charge(s1,r1.epsilon);s1.rollback();s1.close()#模拟扣费后提交前中断
 with T() as s:b=budget_view(s)
 check('中断时扣费随事务回滚',charged and abs(b['spent'])<1e-9,str(b))
 with T() as s:o=process_release(s,crid)
 with T() as s:
  r=s.get(Release,crid);first=json.dumps(r.result,sort_keys=True);b=budget_view(s);expected=json.dumps(build_result(r,snapshot),sort_keys=True)
 check('中断重试后单次扣费且结果确定一致',o=='published' and abs(b['spent']-0.4)<1e-9 and first==expected,f'spent={b["spent"]}')
 with T() as s:
  o2=process_release(s,crid);r=s.get(Release,crid);second=json.dumps(r.result,sort_keys=True);b2=budget_view(s)
 check('已发布重试：不重抽噪声、不重复扣费',o2=='skip' and first==second and abs(b2['spent']-0.4)<1e-9)
 # 5. 共享最小化：共享入口与导出仅含扰动结果
 with T() as s:
  r=s.get(Release,crid);shared=shared_view(r);dumped=dump_release(r)
 text=json.dumps(shared,ensure_ascii=False);forbidden={'snapshot','events','members','visited','missing','noise_seed','learner','occurred_at'}
 check('共享入口不含工号与原始快照','CQ-' not in text and not (keys(shared,set())&forbidden),str(keys(shared,set())&forbidden))
 check('管理视图不泄露噪声种子','noise_seed' not in dumped)
 check('整表隐私保证随结果发布','差分隐私' in r.result['guarantee'] and 'Δ=5' in r.result['guarantee'] and 'Laplace' in r.result['guarantee'])
finally:
 with admin.connect() as c:c.execution_options(isolation_level='AUTOCOMMIT').execute(text('DROP DATABASE IF EXISTS cohort_dp_verify'))
failed=[n for n,ok in CHECKS if not ok]
print(f'\n{len(CHECKS)-len(failed)}/{len(CHECKS)} 项通过');sys.exit(1 if failed else 0)
