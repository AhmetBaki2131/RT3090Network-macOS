#!/usr/bin/env python3
"""Execute the shipped shell logic with stand-ins for macOS-only commands."""
from pathlib import Path
import tempfile,subprocess,os
r=Path(__file__).resolve().parent.parent
s=(r/'tools/rt3090-test.command').read_text()
with tempfile.TemporaryDirectory() as td:
 p=Path(td);root=p/'package with spaces';root.mkdir();(root/'RT3090Network.kext/Contents/MacOS').mkdir(parents=True)
 (root/'RT3090Network.kext/Contents/Info.plist').write_text('fixture');(root/'RT3090Network.kext/Contents/MacOS/RT3090Network').write_text('fixture')
 stub=p/'mac-command';stub.write_text('''#!/usr/bin/env python3
import os,sys,shutil,pathlib
name=sys.argv[1];args=sys.argv[2:]
with open(os.environ['TRACE'],'a') as f:f.write(name+' '+ ' '.join(args)+'\\n')
if name=='id':print('0')
elif name=='PlistBuddy':print('org.rt3090.network' if 'CFBundleIdentifier' in args[1] else '0.3.4')
elif name=='kextstat':
 print('Index Refs Address Size Wired Name (Version)')
 if os.environ.get('LOADED')=='1':print('69 0 0x1 0x2 0x2 org.rt3090.network (0.3.3)')
elif name=='ditto':shutil.copytree(args[0],args[1])
elif name=='kextutil' and '-n' in args and os.environ.get('FAIL_VALIDATE')=='1':sys.exit(42)
''');stub.chmod(0o755)
 for cmd in ['id','PlistBuddy','plutil','kextstat','ditto','chown','chmod','kextutil','kextunload']:
  for folder in ['/usr/bin','/bin','/usr/sbin','/usr/libexec']:
   s=s.replace(folder+'/'+cmd+' ', '"'+str(stub)+'" '+cmd+' ')
 s=s.replace('/private/tmp/rt3090-test.XXXXXX',str(p/'rt3090-test.XXXXXX'))
 script=root/'rt3090-test.command';script.write_text(s);script.chmod(0o755)
 for action,loaded,fail in [('check',False,False),('load',False,False),('load',False,True),('load',True,False)]:
  trace=p/'trace';trace.write_text('');env=os.environ.copy();env.update(TRACE=str(trace),LOADED=str(int(loaded)),FAIL_VALIDATE=str(int(fail)))
  result=subprocess.run(['bash',str(script),action],capture_output=True,text=True,env=env)
  log=trace.read_text();lines=log.splitlines();loads=[line for line in lines if line.startswith('kextutil -v')]
  assert result.returncode==(42 if fail else 1 if loaded else 0),(result.returncode,result.stderr,log)
  assert len(loads)==(1 if action=='load' and not fail and not loaded else 0),log
  assert not list(p.glob('rt3090-test.*')), 'staging directory not cleaned'
print('PASS shipped shell flow: check never loads; load validates first; validation error and existing module stop load; spaced paths and cleanup; macOS commands are shims.')
