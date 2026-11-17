import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import Cohort,Release
from src.services.analysis import calculate
from src.services.privacy import process_release
rc=redis.Redis.from_url(os.environ['REDIS_URL'])
with Session() as recovery:
 for pending in recovery.query(Cohort).filter(Cohort.state.in_(['queued','running'])).all():
  pending.state='queued';rc.rpush('cohort:jobs',pending.id)
 for pending in recovery.query(Release).filter(Release.state=='pending').all():
  rc.rpush('release:jobs',pending.id)
 recovery.commit()
while True:
 Path('/tmp/heartbeat').touch()
 try:
  item=rc.blpop(['release:jobs','cohort:jobs'],timeout=3)
  if not item:continue
  queue=item[0].decode() if isinstance(item[0],bytes) else item[0]
  if queue=='release:jobs':
   ident=int(item[1])
   try:
    with Session() as s:process_release(s,ident)
   except Exception:
    logging.exception('release %s',ident);time.sleep(2);rc.rpush('release:jobs',ident)
   continue
  with Session() as s:
   row=s.get(Cohort,int(item[1]))
   if not row or row.state!='queued':continue
   snapshot=row.result['snapshot'];row.state='running';s.commit()
   try:
    row.result={**calculate(snapshot),'snapshot':snapshot};row.state='done'
    Path('/artifacts/'+str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
   except Exception as e:row.state='failed';row.error=str(e)
   s.commit()
 except Exception:logging.exception('worker');time.sleep(2)
