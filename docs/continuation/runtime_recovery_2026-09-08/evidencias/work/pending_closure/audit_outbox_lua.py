"""Independent ACL audit of the exact C# Lua source, synthetic UUID keys only."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

import redis

import provision_redis_wsl as provision

REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')


def cs_constant(source, name):
    match = re.search(rf'const string {name} = (Checks \+ (?:"\\n" \+ )?)?"""\s*(.*?)\s*""";', source, re.S)
    if not match:
        raise ValueError('constant absent: ' + name)
    prefix = cs_constant(source, 'Checks') if match.group(1) else ''
    if match.group(1) and '"\\n"' in match.group(1):
        prefix += '\n'
    return prefix + match.group(2)


def connection(user=None):
    return redis.Redis(host='127.0.0.1', port=provision.PORT, db=12, username=user,
                       password='' if user else None, decode_responses=True, socket_timeout=3)


def audit_case(default, script, denial):
    prefix = 'pending-audit-' + uuid4().hex + ':'
    user = 'pending_audit_' + uuid4().hex
    keys = [prefix + value for value in ('current', 'fair', 'request', 'lineup', 'marker', 'ready', 'outbox')]
    invocation = {'protocol_version': 'brasileirao.redis/2', 'run_id': prefix + 'run',
                  'job_id': prefix + 'job', 'match_id': prefix + 'match', 'state_version': '1'}
    payload = json.dumps(invocation, separators=(',', ':'))
    fair = json.dumps(invocation | {'1': 2.0})
    signal = {'RunId': invocation['run_id'], 'JobId': invocation['job_id'],
              'MatchId': invocation['match_id'], 'StateVersion': '1', 'Market': '1', 'Synthetic': True}
    args = [payload, fair, 'lineup', prefix + 'signals', json.dumps(signal)]
    default.set(keys[0], payload, px=30000)
    default.set(keys[1], fair, px=5000)
    default.hset(keys[2], mapping={'payload': payload, 'result': fair, 'lineup_state': args[2], 'status': 'completed'})
    default.pexpire(keys[2], 30000)
    default.set(keys[3], args[2], px=30000)
    default.zadd(keys[5], {invocation['run_id']: 1})
    restricted = None
    try:
        default.execute_command('ACL', 'SETUSER', user, 'on', 'nopass', '~' + prefix + '*', '&' + prefix + '*', '+@all', '-' + denial)
        restricted = connection(user)
        failure, reply = None, None
        try:
            reply = restricted.eval(script, len(keys), *keys, *args)
        except redis.ResponseError as exc:
            failure = str(exc)
        after_denial = {'marker': default.exists(keys[4]), 'outbox_count': default.xlen(keys[6]),
                        'ready_present': default.zscore(keys[5], invocation['run_id']) is not None}
        replay = default.eval(script, len(keys), *keys, *args)
        final = {'marker': default.exists(keys[4]), 'outbox_count': default.xlen(keys[6]),
                 'ready_present': default.zscore(keys[5], invocation['run_id']) is not None}
        entry = default.xrange(keys[6])[0][1]
        assert json.loads(entry['batch_json']) == [signal]
        assert entry['run_id'] == invocation['run_id'] and entry['state_version'] == '1'
        if denial == 'publish':
            assert failure is None and reply == 1 and replay == 0
            assert after_denial == {'marker': 1, 'outbox_count': 1, 'ready_present': False}
        else:
            assert failure is not None and reply is None and replay == 1
            assert after_denial == {'marker': 0, 'outbox_count': 0, 'ready_present': True}
        assert final == {'marker': 1, 'outbox_count': 1, 'ready_present': False}
        return {'denied_command': denial, 'error': failure, 'reply': reply, 'after_denial': after_denial,
                'allowed_replay': replay, 'final': final, 'batch_identity_and_payload_preserved': True, 'passed': True}
    finally:
        if restricted:
            restricted.close()
        default.execute_command('ACL', 'DELUSER', user)
        default.delete(*keys)


def main():
    ready = json.loads((provision.BASE / 'ready.json').read_text(encoding='utf-8'))
    info = provision.server_info()
    assert info['run_id'] == ready['run_id'] and str(info['process_id']) == str(ready['process_id'])
    path = REPO / 'dotnet/LineupWorker/Services/KernelRedisProtocolV2.cs'
    source = path.read_bytes()
    script = cs_constant(source.decode('utf-8'), 'PublishSignals')
    dest = Path(__file__).resolve().parent / ('outbox_acl_' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S'))
    dest.mkdir(exist_ok=False)
    (dest / 'KernelRedisProtocolV2.cs.snapshot').write_bytes(source)
    result = {'at_utc': datetime.now(UTC).isoformat(), 'run_id': ready['run_id'], 'process_id': ready['process_id'],
              'url': 'redis://127.0.0.1:26380/12', 'source_path': str(path),
              'source_sha256': hashlib.sha256(source).hexdigest(), 'script_sha256': hashlib.sha256(script.encode()).hexdigest(),
              'synthetic_only': True, 'global_cleanup_used': False, 'cases': [], 'passed': False}
    default = connection()
    try:
        assert default.info('server')['run_id'] == ready['run_id']
        result['dbsize_before'] = default.dbsize()
        for denied in ('xadd', 'set', 'zrem', 'publish'):
            result['cases'].append(audit_case(default, script, denied))
        result['dbsize_after'] = default.dbsize()
        assert result['dbsize_before'] == result['dbsize_after']
        result['passed'] = True
    finally:
        default.close()
        with (dest / 'audit.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
