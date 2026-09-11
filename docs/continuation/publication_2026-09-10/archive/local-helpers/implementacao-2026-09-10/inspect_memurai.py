"""Read a public software distribution page, without account, form submission or install."""
import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
url='https://www.memurai.com/get-memurai'
started=datetime.now(UTC).isoformat()
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40) as response:
    raw=response.read(2_000_000)
    status=response.status
(root/'memurai-download-page.html').write_bytes(raw)
text=raw.decode('utf-8')
links=sorted(set(re.findall(r'''https?[^\s<>"']+(?:\.msi|\.zip|\.exe)[^\s<>"']*''',text)))
scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',text)
(root/'software-source.json').write_text(json.dumps({'url':url,'requested_at':started,'received_at':datetime.now(UTC).isoformat(),
 'http_status':status,'sha256':hashlib.sha256(raw).hexdigest(),'download_links':links,'script_sources':scripts},indent=2),encoding='utf-8')
print(json.dumps({'download_links':links,'scripts':scripts[-6:]}))
