from sqlalchemy import Column,Integer,String,JSON,Text,ForeignKey,Numeric
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Event(Base):
 __tablename__='events'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False);learner=Column(String(60),nullable=False,index=True);occurred_at=Column(String(40),nullable=False);course=Column(String(40));note=Column(Text,default='')
class Cohort(Base):
 __tablename__='cohorts'
 id=Column(Integer,primary_key=True);name=Column(String(100));start_week=Column(String(10));end_week=Column(String(10));as_of=Column(String(10));horizon=Column(Integer);state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Intervention(Base):
 __tablename__='interventions'
 id=Column(Integer,primary_key=True);cohort_id=Column(Integer,ForeignKey('cohorts.id'));cohort_week=Column(String(10));week_index=Column(Integer);note=Column(Text);members=Column(JSON);status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
class Release(Base):
 __tablename__='releases'
 id=Column(Integer,primary_key=True);request_id=Column(String(64),unique=True,nullable=False);cohort_id=Column(Integer,ForeignKey('cohorts.id'),nullable=False);name=Column(String(100));epsilon=Column(Numeric(6,4),nullable=False);state=Column(String(20),default='pending');result=Column(JSON,nullable=True);error=Column(Text,default='');noise_seed=Column(String(64));created_by=Column(String(100));created=Column(String(40));published=Column(String(40))
class PrivacyBudget(Base):
 __tablename__='privacy_budget'
 id=Column(Integer,primary_key=True);total=Column(Numeric(8,4),nullable=False);spent=Column(Numeric(8,4),nullable=False,default=0)
