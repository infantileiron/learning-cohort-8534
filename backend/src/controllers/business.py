from fastapi import HTTPException
from src.models.entities import Cohort,Intervention
def ensure_cohort(s,i):
 r=s.get(Cohort,i)
 if not r:raise HTTPException(404,'队列方案不存在')
 return r
def ensure_intervention(s,i):
 r=s.get(Intervention,i)
 if not r:raise HTTPException(404,'干预清单不存在')
 return r
