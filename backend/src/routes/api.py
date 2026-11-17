import os,json
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Event,Cohort,Intervention,Audit
from src.schemas.business import Login,EventInput,CohortInput,InterventionInput,NoteInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services.interventions import draft
from src.controllers.business import ensure_cohort,ensure_intervention
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/events')
def events(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Event).order_by(Event.id.desc()).all()]
@router.post('/events')
def event(data:EventInput,u=Depends(editor),s=Depends(db)):
 existing=s.query(Event).filter_by(code=data.code).first()
 if existing:
  if all(getattr(existing,k)==v for k,v in data.model_dump().items()):return dump(existing)
  raise HTTPException(409,'同事件编号的内容冲突，请修订原记录或使用新编号')
 r=Event(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:
  s.rollback();other=s.query(Event).filter_by(code=data.code).first()
  if other and all(getattr(other,k)==v for k,v in data.model_dump().items()):return dump(other)
  raise HTTPException(409,'同事件编号的内容冲突')
 audit(s,u,'录入学习事件 '+r.code);return dump(r)
@router.put('/events/{i}')
def edit_event(i:int,data:EventInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Event,i)
 if not r:raise HTTPException(404,'事件不存在')
 for k,v in data.model_dump().items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'事件编号重复')
 audit(s,u,'修订学习事件 '+str(i));return dump(r)
@router.get('/cohorts')
def cohorts(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Cohort).order_by(Cohort.id.desc()).all()]
@router.post('/cohorts')
def cohort(data:CohortInput,u=Depends(editor),s=Depends(db)):
 cfg=data.model_dump(mode='json');snapshot={'config':cfg,'events':[dump(r) for r in s.query(Event).order_by(Event.id).all()]};r=Cohort(**cfg,result={'snapshot':snapshot});s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('cohort:jobs',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，请稍后重试';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交留存队列 '+str(r.id));return dump(r)
@router.get('/cohorts/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_cohort(s,i))
@router.get('/cohorts/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_cohort(s,i)
 if r.state!='done':raise HTTPException(409,'计算成功后才能导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="learning-cohort-{i}.json"'})
@router.get('/interventions')
def interventions(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Intervention).order_by(Intervention.id.desc()).all()]
@router.post('/interventions')
def intervention(data:InterventionInput,u=Depends(editor),s=Depends(db)):
 r=draft(s,ensure_cohort(s,data.cohort_id),data);audit(s,u,'生成干预清单 '+str(r.id));return dump(r)
@router.put('/interventions/{i}')
def edit_intervention(i:int,data:NoteInput,u=Depends(editor),s=Depends(db)):
 r=ensure_intervention(s,i)
 if r.status!='draft':raise HTTPException(409,'已签核清单不可修改')
 r.note=data.note;s.commit();audit(s,u,'修订干预说明 '+str(i));return dump(r)
@router.post('/interventions/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=ensure_intervention(s,i)
 if r.status!='draft':raise HTTPException(409,'已签核，不可重复签核')
 r.status='approved';s.commit();audit(s,u,'签核干预清单 '+str(i));return dump(r)
@router.get('/interventions/{i}/export')
def action_export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_intervention(s,i);return dump(r)
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
