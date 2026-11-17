import hashlib,hmac,math,secrets
from datetime import datetime,timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from src.models.entities import Release,PrivacyBudget,Cohort
from src.services.analysis import calculate
TOTAL_EPSILON=Decimal('1')#全站累计隐私预算
def sensitivity(horizon):return horizon+2#任一学员最多改变1个首学人数与horizon+1个成熟周回访计数
def _u01(seed,label):
 n=int.from_bytes(hmac.new(seed,label.encode(),hashlib.sha256).digest()[:8],'big')>>11
 return (n+1.0)/(2**53+1.0)#开区间(0,1)，避免log(0)
def laplace(seed,label,scale):
 u=_u01(seed,label)-0.5;mag=-math.log1p(-2.0*abs(u))
 return scale*(mag if u>=0 else -mag)
def _vector(calc):
 v=[]
 for row in calc['rows']:
  v.append(row['size'])
  v+=[c['active'] for c in row['cells'] if c['mature']]
 return v
def true_vector(snapshot):return _vector(calculate(snapshot))
def build_result(release,snapshot):
 calc=calculate(snapshot);horizon=snapshot['config']['horizon'];sens=sensitivity(horizon);eps=float(release.epsilon);scale=sens/eps;seed=bytes.fromhex(release.noise_seed);rows=[]
 for row in calc['rows']:
  w=row['cohort_week'];cells=[]
  for c in row['cells']:
   if not c['mature']:continue
   cells.append({'week_index':c['week_index'],'target_week':c['target_week'],'active_noisy':round(c['active']+laplace(seed,f"active:{w}:{c['week_index']}",scale),4)})
  rows.append({'cohort_week':w,'iso_label':row['iso_label'],'size_noisy':round(row['size']+laplace(seed,f"size:{w}",scale),4),'cells':cells})
 guarantee=(f'本表为差分隐私发布，仅含扰动计数，不含工号与原始快照。相邻数据集定义为“增删同一学员（工号）的全部学习事件”。'
  f'发布向量为固定观察窗内各首学周人数与成熟周回访人数；任一学员最多改变1个首学人数与{horizon+1}个回访计数，整表L1敏感度Δ={sens}。'
  f'对每个计数独立加入Laplace(0,b)噪声，b=Δ/ε={round(scale,4)}；整表一次性发布满足ε={eps}的纯差分隐私（δ=0）。'
  f'扰动值可能为负或小数，页面取整与截断属后处理，不额外消耗预算。全站累计预算ε_total=1，本次消耗自发布生效起记入，撤回不返还。')
 return {'kind':'dp-release','mechanism':'laplace-user-level','epsilon':eps,'sensitivity':sens,'noise_scale':round(scale,4),'adjacency':'增删同一学员全部学习事件','timezone':calc['timezone'],'as_of':calc['as_of'],'window':{'start_week':snapshot['config']['start_week'],'end_week':snapshot['config']['end_week'],'horizon':horizon},'rows':rows,'guarantee':guarantee}
def charge(s,epsilon):
 res=s.execute(update(PrivacyBudget).where(PrivacyBudget.id==1,PrivacyBudget.spent+epsilon<=PrivacyBudget.total).values(spent=PrivacyBudget.spent+epsilon).execution_options(synchronize_session=False))
 return res.rowcount==1
def process_release(s,release_id):
 r=s.get(Release,release_id)
 if not r or r.state!='pending':return 'skip'#已发布/已拒绝/已撤回：重试保持一致，不重抽噪声、不重复扣费
 cohort=s.get(Cohort,r.cohort_id)
 if not cohort or cohort.state!='done' or not cohort.result or 'snapshot' not in cohort.result:
  r.state='failed';r.error='冻结方案不存在或尚未计算成功';s.commit();return 'failed'
 try:result=build_result(r,cohort.result['snapshot'])
 except Exception as e:
  r.state='failed';r.error=str(e)[:500];s.commit();return 'failed'
 if not charge(s,r.epsilon):
  r.state='rejected';r.error='隐私预算不足，本次发布被拒绝，未扣减预算';s.commit();return 'rejected'
 r.result=result;r.state='published';r.published=datetime.now(timezone.utc).isoformat();s.commit();return 'published'#预算扣减与结果可见同一事务生效
def create_release(s,data,actor):
 existing=s.query(Release).filter_by(request_id=data.request_id).first()
 if existing:return existing,False#幂等重试：同一request_id不重复建单、不重复扣费
 cohort=s.get(Cohort,data.cohort_id)
 if not cohort or cohort.state!='done':raise HTTPException(409,'仅可发布已计算成功的冻结方案')
 budget=s.get(PrivacyBudget,1)
 if budget and budget.spent+data.epsilon>budget.total:raise HTTPException(409,'隐私预算不足：剩余'+str(float(budget.total-budget.spent))+'，本次申请'+str(float(data.epsilon)))
 r=Release(cohort_id=data.cohort_id,name=data.name,epsilon=data.epsilon,request_id=data.request_id,noise_seed=secrets.token_hex(32),state='pending',created_by=actor,created=datetime.now(timezone.utc).isoformat())
 s.add(r)
 try:s.commit()
 except IntegrityError:
  s.rollback();other=s.query(Release).filter_by(request_id=data.request_id).first()
  if other:return other,False
  raise HTTPException(409,'请求编号冲突，请重试')
 return r,True
def dump_release(r):
 d={c.name:getattr(r,c.name) for c in r.__table__.columns if c.name!='noise_seed'}
 d['epsilon']=float(d['epsilon']);return d
def shared_view(r):
 return {'id':r.id,'name':r.name,'epsilon':float(r.epsilon),'published':r.published,'result':r.result}
def budget_view(s):
 b=s.get(PrivacyBudget,1)
 return {'total':float(b.total),'spent':float(b.spent),'remaining':float(b.total-b.spent)}
