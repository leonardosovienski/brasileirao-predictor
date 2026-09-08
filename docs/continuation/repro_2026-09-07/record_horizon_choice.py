from pathlib import Path

ROOTS = [
    Path('C:/Users/Superleo13/projetos/brasileirao-predictor'),
    Path(__file__).resolve().parent/'brasileirao-predictor',
]
checkpoint = '''> ## CHECKPOINT — HORIZONTE (b) ACEITO PELO OPERADOR (2026-09-07)
>
> O operador respondeu "faz essa" à recomendação (b). Decisão: preservar
> H14/H15, retomar coleta passiva e direcionar pesquisa ativa a B/C/D
> (preço/execução/estrutural); não dedicar pesquisa ativa a outcomes.
> **Supersede o status de horizonte pendente** do checkpoint anterior e das
> entregas da auditoria de 07/09. Não supersede protocolos/resultados.
>
> Preparação: backup consistente do SQLite via API de backup, cópia dos
> ledgers/estados protegidos e exportação XML das sete tarefas envolvidas.
> Ambiente operacional conservado em 7b5f833, core3.1.0/ops4.0.0; não subir
> versões nem aplicar alterações de avaliação da auditoria anterior aqui.
> Fontes/modelos/configuração/contratos protegidos preservados por SHA-256.
>
> Escopo autorizado: H14/H15 (15min), infraestrutura de atualização de
> fixtures/cache (6h) e A1 econômico (15min, quatro janelas por evento),
> discovery semanal e métricas operacionais diárias. Sem avaliações
> intermediárias, alteração de hipóteses, capital, gasto ou dados pagos.
> A1: chave rotacionada atestada; fingerprint inicializado confere; conta
> consultada sem consumo tarifado: 58/250, reserva20, margem172 em 18:17Z.
> Não é promessa de cobertura ou homologação; permanece REHEARSAL_ONLY.
>
> Retomada em preparação: conferir checkpoint de conclusão operacional
> acima deste antes de afirmar que tarefas voltaram a operar.

'''
for root in ROOTS:
    target = root/'HANDOFF.md'
    original = target.read_bytes()
    newline = b'\r\n' if b'\r\n' in original[:200] else b'\n'
    first, rest = original.split(newline,1)
    encoded = checkpoint.replace('\n',newline.decode()).encode('utf-8')
    target.write_bytes(first+newline+newline+encoded+rest.lstrip(b'\r\n'))
local = ROOTS[0]/'jobs.market-research.example.json'
payload = local.read_bytes()
old = b'"scripts/update_h9_fixtures.py"'
new = b'"brasileirao_scripts/update_h9_fixtures.py"'
assert payload.count(old)==1
local.write_bytes(payload.replace(old,new,1))
print('Horizon (b) recorded; one fixture job path corrected; scientific configuration preserved.')
