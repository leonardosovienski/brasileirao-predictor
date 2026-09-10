"""One prespecified independent DC observation diagnostic; no outcomes or API."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
DC = Path('C:/BRASILEIRAO/work/data-completion-2026-09-09/prospective_pilot')
sys.path.insert(0, str(REPO))
sys.dont_write_bytecode = True
allowed = {DC / 'receipt.json', DC / 'selected_fixture.json', *(DC / f'capture_{n:02d}.json' for n in (1, 2, 3))}


def guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.system', 'os.exec', 'os.spawn', 'sqlite3.connect')):
        raise PermissionError('economic_experiment_has_no_network_process_or_database')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        target = Path(args[0]).resolve()
        if target.is_relative_to(DC.parent) and target not in allowed:
            raise PermissionError('only_frozen_independent_capture_inputs')
        if target.is_relative_to(REPO / 'data') or target.is_relative_to(REPO / 'reports') or target.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')) or target.name == '.env':
            raise PermissionError('protected_input_forbidden')
        if any(c in (args[1] or '') for c in 'wax+') and not target.is_relative_to(ROOT):
            raise PermissionError('write_outside_experiment')


sys.addaudithook(guard)
from brasileirao_predictor.research.price_strength.capture_decision import main
from brasileirao_predictor.research.price_strength.live_capture_admission import strict_json_loads

assert hashlib.sha256((DC / 'selected_fixture.json').read_bytes()).hexdigest() == 'b9d6254e91e49aa8fabf888278200d9c1ba7fc4dacdacffc98045a757d5d77e4'
receipt = strict_json_loads((DC / 'receipt.json').read_bytes())
names = [f'capture_{n:02d}.json' for n in (1, 2, 3)]
rows = [r for r in receipt['requests'] if r.get('file') in names]
assert len(rows) == 3
contract = {
    'schema_version': 'api-capture-decision/1', 'fixture_id': 'id1000032566887012',
    'identity': {'participant1Id': 1982, 'participant2Id': 1967, 'sportId': 10, 'tournamentId': 325, 'seasonId': 137706},
    'kickoff_at': '2026-09-12T00:00:00Z', 'decision_at': max(r['received_at'] for r in rows),
    'initial_bankroll_units': 100,
    'policy': {'reference_books': ['pinnacle'], 'max_age_seconds': 120, 'max_skew_seconds': 15,
               'cost_per_unit': 0.02, 'commission_on_profit': 0.0},
}
contract_path = ROOT / 'capture-experiment-contract.json'
contract_bytes = (json.dumps(contract, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
if contract_path.exists():
    frozen = contract_path.read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == 'b9772195bab969a6ca0f9429eb390cf4b2c7765208ab54b77e4c0dfa63551f49'
    assert strict_json_loads(frozen) == contract
else:
    with contract_path.open('xb') as file:
        file.write(contract_bytes)
attempt = sys.argv[1] if len(sys.argv) == 2 else '01'
assert attempt.isascii() and attempt.isdigit()
argv = ['--contract', str(contract_path), '--receipt', str(DC / 'receipt.json'), '--output-dir', str(ROOT / ('capture-experiment-' + attempt))]
for name in names:
    argv.extend(['--capture', str(DC / name)])
raise SystemExit(main(argv))
