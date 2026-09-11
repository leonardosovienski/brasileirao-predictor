"""Bounded, sanitized Windows child runner. Not an OS filesystem sandbox."""
import ctypes
from ctypes import wintypes as wt
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
PYTHON=pathlib.Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/managed-python/cpython-3.13-windows-x86_64-none/python.exe')
TEMP=pathlib.Path('C:/BRASILEIRAO/work/open-source-research-OSR-20260911-03/tmp')

class Basic(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),('LimitFlags',wt.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wt.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wt.DWORD),('SchedulingClass',wt.DWORD)]
class Io(ctypes.Structure):
    _fields_=[(x,ctypes.c_uint64) for x in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
class Extended(ctypes.Structure):
    _fields_=[('BasicLimitInformation',Basic),('IoInfo',Io),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]

def run(script,receipt,timeout=120):
    target=(HERE/script).resolve()
    if target.parent!=HERE or not target.is_file():raise ValueError('explicit local script only')
    receipt_path=ROOT/'evidence'/receipt
    if receipt_path.exists():raise FileExistsError(receipt_path)
    env={k:os.environ[k] for k in ['SystemRoot','WINDIR'] if k in os.environ}
    env.update(TEMP=str(TEMP),TMP=str(TEMP),PATH=str(PYTHON.parent),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONHASHSEED='0')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wt.LPCWSTR];k.CreateJobObjectW.restype=wt.HANDLE
    k.SetInformationJobObject.argtypes=[wt.HANDLE,ctypes.c_int,ctypes.c_void_p,wt.DWORD];k.SetInformationJobObject.restype=wt.BOOL
    k.AssignProcessToJobObject.argtypes=[wt.HANDLE,wt.HANDLE];k.AssignProcessToJobObject.restype=wt.BOOL
    k.TerminateJobObject.argtypes=[wt.HANDLE,wt.UINT];k.TerminateJobObject.restype=wt.BOOL
    k.CloseHandle.argtypes=[wt.HANDLE];k.CloseHandle.restype=wt.BOOL
    job=k.CreateJobObjectW(None,None)
    if not job:raise ctypes.WinError(ctypes.get_last_error())
    limits=Extended();limits.BasicLimitInformation.LimitFlags=0x2000|0x100|0x8
    limits.BasicLimitInformation.ActiveProcessLimit=1;limits.ProcessMemoryLimit=768*1024*1024
    if not k.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
        k.CloseHandle(job);raise ctypes.WinError(ctypes.get_last_error())
    command=[str(PYTHON),'-I','-S','-B','-X','utf8',str(HERE/'child_boot.py'),str(target)]
    start=time.perf_counter();p=None;timed_out=False
    try:
        p=subprocess.Popen(command,env=env,cwd=TEMP,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
        if not k.AssignProcessToJobObject(job,wt.HANDLE(p._handle)):
            p.kill();p.communicate();raise ctypes.WinError(ctypes.get_last_error())
        try:out,err=p.communicate('GO\n',timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;k.TerminateJobObject(job,124);out,err=p.communicate(timeout=5)
    finally:
        k.CloseHandle(job)
    rec={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'cwd':str(TEMP),'env_keys':sorted(env),'environment_policy':'explicit allowlist; no inherited secret values','job_memory_mib':768,'job_active_process_limit':1,'job_assigned':True,'timeout_seconds':timeout,'timed_out':timed_out,'exit_code':p.returncode,'elapsed_wall_seconds':time.perf_counter()-start,'stdout':out,'stderr':err,'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    receipt_path.write_text(json.dumps(rec,indent=2),encoding='utf-8')
    print(json.dumps({k:rec[k] for k in ['command','exit_code','timed_out','elapsed_wall_seconds','stdout','stderr']}))
    return rec

if __name__=='__main__':
    rec=run(sys.argv[1],sys.argv[2],float(sys.argv[3]) if len(sys.argv)>3 else 120)
    sys.exit(0 if rec['exit_code']==0 or (sys.argv[1]=='timeout_probe.py' and rec['timed_out']) else 1)
