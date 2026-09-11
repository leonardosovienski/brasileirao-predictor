"""Install verified portable SDK and copy only public runtime sources for build."""
import hashlib
import json
import shutil
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path('C:/BRASILEIRAO/brasileirao-predictor')

def main():
    data=json.loads((ROOT/'public-sources/dotnet_10_release_metadata.raw').read_bytes())
    sdk=next(s for r in data['releases'] for s in r.get('sdks',[r['sdk']]) if s['version']==data['latest-sdk'])
    source=next(f for f in sdk['files'] if f['rid']=='win-x64' and f['url'].endswith('.zip'))
    if not source['url'].startswith('https://builds.dotnet.microsoft.com/dotnet/Sdk/'):
        raise ValueError('unexpected_sdk_origin')
    archive=ROOT/'dotnet-sdk.zip'
    with urllib.request.urlopen(source['url'],timeout=45) as response, archive.open('xb') as out:
        shutil.copyfileobj(response,out)
    actual=hashlib.sha512(archive.read_bytes()).hexdigest()
    assert actual==source['hash'],'sdk_integrity_failed'
    install=ROOT/'dotnet-sdk'
    install.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not (install/member.filename).resolve().is_relative_to(install):
                raise ValueError('archive_path_escape')
        z.extractall(install)
    workspace=ROOT/'dotnet-work'
    workspace.mkdir(exist_ok=False)
    shutil.copytree(REPO/'dotnet',workspace/'dotnet')
    shutil.copytree(REPO/'contracts',workspace/'contracts')
    for name in ('global.json','config.yaml','compose.yaml'):
        shutil.copy2(REPO/name,workspace/name)
    (ROOT/'dotnet-sdk-receipt.json').write_text(json.dumps({'at':datetime.now(UTC).isoformat(),'sdk':sdk['version'],'url':source['url'],'sha512':actual,'bytes':archive.stat().st_size,'source_metadata_sha256':hashlib.sha256((ROOT/'public-sources/dotnet_10_release_metadata.raw').read_bytes()).hexdigest(),'install':str(install),'workspace':str(workspace)},indent=2)+'\n',encoding='utf-8')
    print('Portable SDK verified and extracted: '+sdk['version'],flush=True)

if __name__=='__main__':
    main()
