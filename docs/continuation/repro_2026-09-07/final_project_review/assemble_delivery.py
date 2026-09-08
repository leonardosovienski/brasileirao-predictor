"""Consolidate the final review and evidence, keeping scientific originals intact."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
LIVE = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
OUT = ROOT/'outputs/REVISAO_FINAL'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'evidencias').mkdir(exist_ok=True)
(OUT/'codigo').mkdir(exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


check_names = ['pytest_release','lint_release','format_release','types_final','dotnet_restore',
               'dotnet_build','dotnet_unit','wheel_final','coverage_gate','env_schema','static_barriers_verified']
checks = {name:read(WORK/(name+'.json')) for name in check_names}
if any(row['exit_code'] for row in checks.values()):
    raise AssertionError('Required available validation failed')
test_log=(WORK/'pytest_release.log').read_text(encoding='utf-8')
assert '1082 passed, 1 deselected' in test_log
baseline=read(ROOT/'outputs/DIVISAO_2026/integridade.json')['protected_sha256']
actual={name:sha(LIVE/name) for name in baseline}
assert baseline==actual,'Protected scientific file changed'
reexecution=read(WORK/'studies_reexecution.json')
assert reexecution['status']=='PASS'
assert read(WORK/'replay_verified/audit_results.json')['status']=='PASS'
coverage=read(WORK/'coverage_final.json')['totals']
for name in check_names:
    for suffix in ('.json','.log'):
        shutil.copy2(WORK/(name+suffix),OUT/'evidencias'/(name+suffix))
for name in ('data_audit.json','data_audit.md','frozen_data_profile.json','operational_code_review.md',
             'METHODOLOGY_FINDINGS.md','DIAGNOSTICO_QUALIDADE.md','diagnostics_quality_results.json',
             'diagnostics_quality_plan.json','diagnostics_quality_verification.json',
             'studies_reexecution.json','scheduled_tasks_final.json','docker_probe.json'):
    path=WORK/name
    if path.exists():
        shutil.copy2(path,OUT/'evidencias'/name)
for name in ('results.json','candidate.json','audit_results.json'):
    shutil.copy2(WORK/'replay_verified'/name,OUT/'evidencias'/('replay_'+name))
for name in ('diagnostics_quality.py','test_diagnostics_quality.py','recheck_studies.py',
             'run_check.py','prepare_snapshot.py'):
    shutil.copy2(WORK/name,OUT/'codigo'/name)
shutil.copy2(WORK/'VALIDAR_REDIS_ISOLADO.ps1',OUT/'VALIDAR_REDIS_ISOLADO.ps1')
sources=['brasileirao_predictor/ingest_sofascore.py','brasileirao_predictor/research/season_2026_split.py',
         'brasileirao_scripts/run_passive_task.py','brasileirao_scripts/exp001_data_pilot.py',
         'brasileirao_scripts/ci_check.py','jobs.market-research.example.json',
         'tests/test_parse_ou_scope_regression.py','tests/test_run_passive_task.py',
         'tests/test_run_passive_process_tree.py','tests/test_market_research_jobs_manifest.py',
         'tests/test_exp001_cutoff_state_regression.py','tests/test_season_2026_split.py',
         'tests/test_ci_current_elo_containment.py']
for name in sources:
    target=OUT/'codigo'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(LIVE/name,target)
diff=subprocess.run(['git','-C',str(LIVE),'diff','--check'],capture_output=True,text=True)
assert diff.returncode==0,diff.stdout+diff.stderr
subprocess.run(['git','-C',str(LIVE),'diff','--output='+str(OUT/'alteracoes_rastreadas.patch')],check=True)
status={
    'reviewed_at_utc':datetime.now(UTC).isoformat(),
    'engineering_status':'AVAILABLE_LOCAL_CHECKS_PASS_INTEGRATION_PENDING',
    'economic_status':'PROFITABILITY_NOT_DEMONSTRATED',
    'real_capital_enabled':False,'orders_placed':0,'parameter_search_on_2026':False,
    'python_tests_passed':1082,'python_redis_tests_not_run':1,
    'research_tests_passed':103,'dotnet_tests_passed':18,'dotnet_redis_tests_not_run':13,
    'full_compose_e2e':'NOT_EXECUTED_DOCKER_SERVICE_UNAVAILABLE',
    'coverage_previous_instrumented_suite_percent':coverage['percent_covered'],
    'protected_files_unchanged':True,'protected_sha256':actual,
    'operational_sources_sha256':{name:sha(LIVE/name) for name in sources},
    'second_turn':{'official_games':190,'evaluated_games':58,'pending_games':132,
        'primary_bets':9,'primary_wins':4,'net_units':-1.23,'roi':-0.1366666666666667,
        'net_brl_at_50_per_bet':-61.50,'max_drawdown_units':3.06,'raw_net_units':-19.495},
    'scientific_fingerprint':reexecution['new_split']['scientific_fingerprint'],
    'rounds_are_not_disjoint_calendar_periods':True,
    'retrospective_odds_execution_proven':False,
    'checks':{name:{'exit_code':row['exit_code'],'seconds':row['seconds']} for name,row in checks.items()}}
(OUT/'estado_final.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
report='''# Revisão final do projeto — 07/09/2026

**O projeto foi revisado, corrigido e reexecutado. Ainda não temos lucro demonstrado.** O novo replay repetiu o prejuízo de **1,23 unidade**, equivalente a **R$61,50 com R$50 por aposta**, nos 58 jogos disponíveis do segundo turno. As melhorias corrigiram falhas de implementação; não criaram uma vantagem econômica nos dados avaliados.

| Resultado da simulação | Calibrado em 2025 | Mesmo modelo sem calibração |
|---|---:|---:|
| Primeiro turno: apostas | 46 | 153 |
| Primeiro turno: saldo líquido | −14,511 u | +0,710 u |
| Segundo turno disponível: apostas | 9 | 46 |
| Segundo turno: acertos / erros | 4 / 5 | 10 / 36 |
| Segundo turno: saldo líquido | **−1,230 u** | **−19,495 u** |
| Segundo turno: ROI líquido | **−13,67%** | **−42,38%** |
| Segundo turno: saldo a R$50 por aposta | **−R$61,50** | **−R$974,75** |

O custo adicional simulado é de 2% do valor apostado, inclusive nas perdas. Com banca inicial de R$5.000 e aposta fixa de R$50, a versão calibrada terminaria o trecho do segundo turno em R$4.938,50. A maior queda desde um pico seria R$153. Os 190 jogos do turno estão preservados; 132 ainda não têm resultado avaliável neste corte. Não é uma previsão do saldo final do campeonato.

Foram corrigidos cinco pontos concretos:

1. **Mercado errado nas odds de gols.** O parser podia aceitar escanteios/cartões, outro período ou cotações conflitantes como total de gols. Reproduzi os erros e fiz os caminhos de ingestão usar a mesma validação de mercado, período, linha e preço. Sem payload histórico, não inventei uma correção retroativa dos preços.
2. **Subprocessos sobrevivendo ao timeout.** O launcher agora encerra somente a árvore que iniciou. Se não conseguir confirmar a limpeza, registra a falha explicitamente. A regressão usa processos sintéticos e comprovou o encerramento.
3. **Chave exposta em erro de conexão.** Exceções de transporte do EXP001 agora são sanitizadas, inclusive o contexto da traceback, preservando os testes com chaves fictícias.
4. **Comandos apontando para caminhos inexistentes.** Dez referências antigas foram corrigidas; os onze comandos do manifesto resolvem para arquivos existentes. Isso não ativou tarefas desabilitadas.
5. **Falso alarme da barreira de Elo.** H14 captura o serving antes do jogo, mas a barreira o classificava como pesquisa retrospectiva. A exceção passou a reconhecer somente esse caminho exato. Quatro regressões continuam bloqueando pesquisas e cópias novas indevidas. O código e o protocolo H14 não foram alterados.

A documentação também foi atualizada: H14/H15 já estão em coleta passiva. Os heartbeats de ambas confirmaram término com código zero usando o novo launcher. As sete agendas previstas continuam habilitadas. Conclusão do processo não significa coleta completa nem lucro.

| Validação executada | Resultado |
|---|---|
| Suíte geral Python sobre o código final isolado | **1.082 aprovados**, 1 integração Redis não executada |
| Replay e diagnóstico probabilístico | **103 aprovados** |
| Ruff e formatação | Aprovados; **344 arquivos** formatados |
| Tipagem Python | **0 erros e 0 avisos** |
| Barreiras de pesquisa somente leitura / Elo | Aprovadas; 10 módulos e 16 arquivos verificados |
| Compilação .NET 10 | Aprovada, sem erros ou avisos |
| Testes .NET sem Redis | **18 aprovados** |
| Pacote Python wheel | Construído no ambiente isolado |
| Cobertura global instrumentada | **50,59%**, acima do limite existente de 45% |
| Hashes científicos protegidos | **14 preservados** |

A suíte executou em worktree separado, com schema de banco vazio e sem copiar credenciais ou dados operacionais. A rede externa dos processos Python foi bloqueada. A cobertura foi medida na execução de 1.078 testes; a execução final acrescentou quatro regressões da barreira CI. A quantidade de testes e o limite de cobertura não provam ausência de todos os defeitos.

**Integração pendente:** o Docker não respondeu e o Windows negou a abertura do serviço para iniciá-lo. Por isso, não homologuei o teste Python com Redis, os 13 testes .NET WorkerRuntime nem o E2E completo do Compose. O script VALIDAR_REDIS_ISOLADO.ps1 foi preparado e teve sua sintaxe validada para executar os testes Redis quando o Docker estiver disponível. Ele usa um Redis descartável em portas locais exclusivas, sem volumes, e não interrompe serviços existentes. Essa parte permanece não executada.

Reexecutei o treino, a calibração e a simulação do candidato fixado, conferindo **760 previsões e 760 decisões**: probabilidades, seleções e saldos se repetiram. Uma implementação independente conferiu os pagamentos. Também reexecutei as **13.680 decisões das 12 políticas históricas de 2023–2025**, sem mudança nos resultados, e conferi **3.214 relações aritméticas da extensão de 51 jogos**, sem divergências. Não houve nova busca de parâmetros em 2026.

Na qualidade probabilística, comparei as previsões nos mesmos jogos com as odds sem margem e com frequências históricas estimadas apenas em 2021–2024. O modelo bruto teve erro médio maior que o mercado nos seis painéis de mercado/turno. Em 1X2 e total de gols, a calibração deu peso zero ao modelo e apenas reproduziu as odds sem margem. Em ambas marcam, a versão calibrada também teve erro maior que o mercado nos dois turnos. Os intervalos por rodada são descritivos, com poucas rodadas no segundo turno e sem ajuste por múltiplas comparações; não transformam o resultado em garantia sobre o futuro.

Eu manteria a coleta passiva e as correções de integridade. Acrescentei os comparadores simples, a incerteza por rodada, a reprodução dos cálculos e um fingerprint científico que não muda só porque a otimização demorou alguns milissegundos a mais. Retiraria este candidato da fila de promoção para apostas reais: o resultado atual não justifica promovê-lo. Não removi evidências antigas nem alterei retrospectivamente seus planos.

Há três limites essenciais na interpretação. **Primeiro**, Elo e parâmetros ficaram congelados no fim de 2024 por escolha do protocolo; isso não reproduz as atualizações contínuas do serving. Atualizar o Elo agora criaria outro candidato após ver os resultados, sem consertar o teste anterior. **Segundo**, os turnos oficiais se sobrepõem no calendário por adiamentos: a rodada 4 teve Flamengo–Mirassol em 02/09, depois do começo do segundo turno em 25/07. Como o primeiro turno não foi usado para ajustar a regra, isso não muda os pagamentos, mas impede dizer que todo o teste terminou antes do início da simulação. **Terceiro**, as odds retrospectivas não têm comprovação de casa, horário de oferta ou execução pré-jogo. Resultados de placares também não têm um histórico completo de revisões.

A verificação externa foi amostral: uma notícia oficial da CBF confirma Cruzeiro 2–1 Flamengo e Internacional 0–0 Atlético-MG, usados no replay. Isso confirma esses dois placares, não as cotações nem os demais 246 jogos; a tabela detalhada apresentou erro de acesso ao abrir. [Fonte: CBF, balanço da 24ª rodada](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-a/a/palmeiras-goleia-vasco-e-volta-a-abrir-vantagem-na-lideranca-do-brasileirao).

**Estado final:** código corrigido e verificações locais disponíveis aprovadas; integração ainda pendente; modelo avaliado sem vantagem econômica demonstrada e com prejuízo no segundo turno disponível. Nenhuma aposta real foi colocada. O arquivo estado_final.json registra esse parecer e os hashes; evidencias contém os relatórios e recibos; codigo contém os arquivos alterados e instrumentos da revisão.
'''
(OUT/'RESULTADO.md').write_text(report,encoding='utf-8')
manifest={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}
(OUT/'sha256.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'output':str(OUT/'RESULTADO.md'),'files':len(manifest),'economic_status':status['economic_status']}))
