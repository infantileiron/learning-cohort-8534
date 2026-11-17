import random
from datetime import date,timedelta,datetime,timezone
from src.config.database import Base,engine,Session
from src.models.entities import User,Event
from src.utils.security import hash_password
def seed():
 Base.metadata.create_all(engine);rng=random.Random(3114);start=date(2026,9,21)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(200):
   first=i//25;learner=f'CQ-{i+1:03}'
   for w in range(first,9):
    if w!=first and rng.random()>.82-.07*(w-first):continue
    day=start+timedelta(weeks=w,days=1+i%3);stamp=day.isoformat()+'T02:00:00+00:00'
    code=f'{learner}-W{w}'
    if not s.query(Event).filter_by(code=code).first():s.add(Event(code=code,learner=learner,occurred_at=stamp,course=('数据素养','服务沟通','安全规范')[i%3],note='学习平台正常上报'))
    if i%17==0:
     code+='-DUP'
     if not s.query(Event).filter_by(code=code).first():s.add(Event(code=code,learner=learner,occurred_at=day.isoformat()+'T04:00:00+00:00',course='数据素养',note='同周重复回访，不重复计人数'))
  s.commit();print({'users':s.query(User).count(),'events':s.query(Event).count(),'learners':len({r.learner for r in s.query(Event).all()})})
if __name__=='__main__':seed()
