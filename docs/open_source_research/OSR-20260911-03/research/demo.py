"""Deterministic executable example; writes only new research receipts."""
import json
from pathlib import Path
from workflow import main
ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    main(['run',str(ROOT/'examples/before.json'),str(ROOT/'evidence/demo_before')])
    main(['run',str(ROOT/'examples/after.json'),str(ROOT/'evidence/demo_after')])
    comparison=main(['compare',str(ROOT/'evidence/demo_before'),str(ROOT/'evidence/demo_after')])
    (ROOT/'evidence/comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf-8')
