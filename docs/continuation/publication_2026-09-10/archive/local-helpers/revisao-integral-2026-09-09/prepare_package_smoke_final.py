from pathlib import Path
p=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
text=(p/'package_smoke.py').read_text(encoding='utf-8').replace("root / 'dist/", "root / 'dist-final/").replace("root / 'package-smoke'", "root / 'package-smoke-final'")
text=text.replace("assert not forbidden, forbidden", "assert not forbidden, forbidden\n    for changed in ['backtest_event.py','simulator.py','temporal_policy.py','research/price_strength/live_capture_admission.py']:\n        name='brasileirao_predictor/'+changed\n        assert archive.read(name)==(Path('C:/BRASILEIRAO/brasileirao-predictor')/name).read_bytes(), name")
(p/'package_smoke_final.py').write_text(text,encoding='utf-8',newline='\n')
