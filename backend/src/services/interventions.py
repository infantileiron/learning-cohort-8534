from fastapi import HTTPException
from src.models.entities import Intervention
def draft(s,cohort,data):
 if cohort.state!='done':raise HTTPException(409,'队列计算完成后才能起草干预')
 row=next((r for r in cohort.result['rows'] if r['cohort_week']==data.cohort_week),None)
 if not row:raise HTTPException(404,'所选首学队列不在该冻结方案中')
 cell=next((c for c in row['cells'] if c['week_index']==data.week_index),None)
 if not cell or not cell['mature']:raise HTTPException(409,'未成熟或超出观察范围的周禁止生成干预')
 if not cell['missing']:raise HTTPException(409,'该成熟周全部回访，没有待干预成员')
 r=Intervention(**data.model_dump(),members=cell['missing']);s.add(r);s.commit();return r
