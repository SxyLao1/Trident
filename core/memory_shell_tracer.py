# -*- coding: utf-8 -*-
"""v1.9.5: Memory Shell Tracer"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from core.log_heuristic import parse_log_line
logger = logging.getLogger(__name__)
_DEF_LB = 24
_WM = {'POST','PUT','PATCH','MKCOL'}
_EX = {'.php','.php5','.phtml','.asp','.aspx','.ashx','.jsp','.jspx','.war','.jar'}
_SD = ['/uploads/','/upload/','/files/','/images/','/wp-content/uploads/','/wp-admin/','/admin/','/tmp/','/druid/']
class MemoryShellTracer:
    def __init__(s, lookback_hours=_DEF_LB): s._lb = lookback_hours
    def trace(s, ip, dt=None, log_paths=None):
        if dt is None: dt = datetime.now()
        start = dt - timedelta(hours=s._lb)
        if log_paths is None: log_paths = s._def_logs()
        entries = []
        for lp in log_paths:
            if not lp.exists(): continue
            for e in s._extract(lp, ip, start, dt): entries.append(e)
        writes = [e for e in entries if e.get('method','').upper() in _WM]
        cands = s._rank(writes)
        m = s._xref(cands)
        conf = 'high' if m else ('medium' if cands else 'low')
        return {'found':len(cands)>0,'ip':ip,'time':dt.isoformat(),'lb':s._lb,'total':len(entries),'writes':len(writes),'candidates':cands[:20],'matched':m,'confidence':conf,'summary':s._sum(ip,len(cands),m)}
    def _extract(s, lp, ip, start, end):
        res = []
        with open(lp,'r',encoding='utf-8',errors='replace') as f:
            for line in f:
                line=line.strip()
                if not line or ip not in line: continue
                p = parse_log_line(line)
                if not p or p.get('ip')!=ip: continue
                try:
                    ts = s._pts(p.get('timestamp',''))
                    if ts and start<=ts<=end: res.append({**p,'_ts':ts})
                except: pass
        res.sort(key=lambda x:x.get('_ts',datetime.min))
        return res
    def _rank(s, entries):
        scored,seen = [],set()
        for e in entries:
            path=e.get('path',''); ext=Path(path).suffix.lower(); m=e.get('method','').upper(); st=e.get('status',0)
            sc=0
            if ext in _EX: sc+=3
            if any(d in path.lower() for d in _SD): sc+=2
            if 200<=st<300: sc+=1
            if st==201: sc+=2
            if m=='POST' and ext in _EX: sc+=2
            if sc>0:
                k=f'{path}|{m}'
                if k not in seen: seen.add(k); scored.append({'path':path,'method':m,'ts':e.get('timestamp',''),'status':st,'score':sc,'ua':e.get('user_agent','')[:200]})
        scored.sort(key=lambda x:x['score'],reverse=True)
        return scored
    def _xref(s, cands):
        if not cands: return None
        try:
            from core.suspicious_registry import get_all
            recs=get_all(include_deleted=False); known={r.get('file_path',''):r for r in recs}
            for c in cands:
                p=c['path']
                if p in known:
                    r=known[p]; return {'fp':p,'detected':r.get('detected_at',''),'feat':r.get('features',[]),'qid':r.get('quarantine_id',''),'match':'exact'}
                n=p.replace('/','')
                for k,v in known.items():
                    if k.endswith(n) or n.endswith(k.replace('/','')): return {'fp':k,'detected':v.get('detected_at',''),'feat':v.get('features',[]),'qid':v.get('quarantine_id',''),'match':'partial'}
        except Exception as e: logger.warning('xref: %s',e)
        return None
    def _def_logs(s):
        ps=[]
        try:
            from config.registry import ConfigRegistry
            lp=ConfigRegistry.get_raw_config().get('website',{}).get('log_config',{}).get('access_log_path','')
            if lp: ps.append(Path(lp))
        except: pass
        for p in ['/var/log/nginx/access.log','/var/log/apache2/access.log']:
            c=Path(p)
            if c.exists() and c not in ps: ps.append(c)
        return ps
    def _pts(s,ts):
        for f in ['%d/%b/%Y:%H:%M:%S %z','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S']:
            try:
                dt = datetime.strptime(ts,f)
                return dt.replace(tzinfo=None)  # strip tz for naive comparison
            except: continue
        try: return datetime.strptime(ts[:19],'%Y-%m-%dT%H:%M:%S')
        except: return None
    def _sum(s,ip,n,m):
        if m: return 'Memory shell traced to ' + m['fp']
        if n: return str(n) + ' suspicious uploads, none matched'
        return 'No upload activity found'

def trace_memory_shell(ip, dt=None, log_paths=None): return MemoryShellTracer().trace(ip, dt, log_paths=log_paths)
def emit_critical_alert(tr):
    try:
        from core.notifier import get_notifier; import logging as _l
        n=get_notifier(_l.getLogger('monitor.notifier'))
        m=tr.get('matched'); t='MEMORY SHELL: ' + (m['fp'].split(chr(92))[-1].split('/')[-1] if m else tr['ip'])
        lines = ['IP: '+tr['ip'], 'Time: '+tr['time'], 'Confidence: '+tr['confidence'], '']
        if m:
            lines += ['WebShell: '+m['fp'], 'Detected: '+m['detected'],
                      'Features: '+','.join(m['feat']),
                      'Q: '+('Yes' if m.get('qid') else 'No'), '']
        if tr.get('candidates'):
            lines.append('Uploads:')
            for c in tr['candidates'][:5]:
                lines.append('  '+c['method']+' '+c['path']+' -> '+str(c['status'])+' (s:'+str(c['score'])+')')
        b = '\n'.join(lines)
        try:
            from core.siem_exporter import emit_detection_event
            emit_detection_event({'id':'ms-'+tr['ip'],'detected_at':tr['time'],'file_path':m.get('fp','') if m else '','features':m.get('feat',[]) if m else [],'source_ip':tr['ip']},category='memory.shell.detected')
        except: pass
        n.send_alert(t,b,level='critical')
        return True
    except Exception as e: logger.error('memshell alert fail: %s',e); return False
