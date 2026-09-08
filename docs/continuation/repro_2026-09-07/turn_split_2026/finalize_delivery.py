"""Finalize split provenance, documentation and verification, without model fitting."""
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[1]
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
DATA = REPO / "data/research/season_2026_turn_split"
OUT = WS / "outputs/DIVISAO_2026"
CONTRACT = REPO / "contracts/season-2026-turn-split-paper.json"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')

source = WS/'work/selection_reanalysis/historical_input.json'
source_manifest = read(WS/'work/selection_reanalysis/input_manifest.json')
assert sha(source) == source_manifest['input_sha256']
historical = read(source)
assert len(historical) == len({row['event_id'] for row in historical}) == 1900
assert all('2021-01-01' <= row['date'] < '2026-01-01' for row in historical)
year_counts = Counter(row['date'][:4] for row in historical)
assert year_counts == {str(y):380 for y in range(2021,2026)}
partition = [{'event_id':row['event_id'], 'season':int(row['date'][:4]),
              'role':'calibration' if row['date'].startswith('2025') else 'train'} for row in historical]
shutil.copyfile(source, DATA/'historical_2021_2025.json')
save(DATA/'historical_partition.json',partition)
contract = read(CONTRACT)
contract['historical_input_source'] = {
    'path':'data/research/season_2026_turn_split/historical_2021_2025.json',
    'sha256':sha(DATA/'historical_2021_2025.json'),
    'partition_path':'data/research/season_2026_turn_split/historical_partition.json',
    'partition_sha256':sha(DATA/'historical_partition.json'),
    'train_events':1520,'calibration_events':380,
    'selection_note':'Reuse the previously verified1900-event snapshot; raw database metadata counts include noncanonical/incomplete rows and are not training sample sizes',
}
contract['provenance_finalized_at'] = datetime.now(timezone.utc).isoformat()
save(CONTRACT,contract)
summary = read(OUT/'resumo.json')
summary['raw_db_metadata_counts_not_training_sample_sizes'] = summary.pop('historical_counts')
summary['verified_historical_events'] = {'train_2021_2024':1520,'calibration_2025':380}
save(OUT/'resumo.json',summary)
shutil.copyfile(CONTRACT,OUT/'contrato.json')
shutil.copyfile(DATA/'historical_partition.json',OUT/'particao_historica.json')
for path in [REPO/'brasileirao_predictor/research/season_2026_split.py',REPO/'tests/test_season_2026_split.py']:
    shutil.copyfile(path,OUT/path.name)
protected = read(WS/'outputs/REANALISE/integridade.json')['protected_sha256']
assert all(sha(REPO/name)==value for name,value in protected.items())
integrity = {'checked_at':datetime.now(timezone.utc).isoformat(),'protected_files_unchanged':True,
             'protected_sha256':protected,'contract_sha256':sha(CONTRACT),
             'schedule_sha256':sha(DATA/'schedule_manifest.json'),
             'classifier_sha256':sha(REPO/'brasileirao_predictor/research/season_2026_split.py'),
             'historical_input_sha256':sha(DATA/'historical_2021_2025.json')}
save(OUT/'integridade.json',integrity)
decision_path = REPO/'docs/decisions/2026-09-07-season-turn-split-paper.md'
decision = decision_path.read_text(encoding='utf-8')
decision += f"\nProveniência finalizada antes de qualquer novo ajuste/avaliação: fonte histórica validada de1900eventos,1520treino e380calibração. SHA final do contrato `{sha(CONTRACT)}` substitui o hash preliminar acima; a divisão e as regras permaneceram iguais.\n"
decision_path.write_text(decision,encoding='utf-8')
(OUT/'DECISAO.md').write_text(decision,encoding='utf-8')
report = f"""# Divisão de dados aplicada para 2026

| Período | Uso definido | Universo |
|---|---|---:|
| 2021–2024 | Treinar e desenvolver o modelo | 1.520 jogos do histórico verificado |
| 2025 | Calibrar probabilidades e escolher a regra | 380 jogos do histórico verificado |
| 2026, rodadas 1–19 | Teste exploratório, sem reajustar o modelo | 190 jogos |
| 2026, rodadas 20–38 | Universo completo da simulação de apostas | 190 jogos |

O segundo turno inteiro está reservado para a etapa de apostas simuladas. Entrar
no universo não obriga apostar: sem modelo congelado, preço válido ou critério
econômico aprovado, o estado é NO_BET. Nenhuma aposta foi executada nesta etapa.

A divisão segue a rodada oficial da [tabela básica da CBF]({contract['round_source']}),
incluindo jogos adiados. A tabela foi conferida por referência, rodada, mandante e
visitante: 380 confrontos únicos, dez por rodada, 19 mandos por clube e confronto
inverso 19 rodadas depois. Não foi usada metade das linhas nem janeiro–junho.

## Situação do segundo turno no congelamento

No instante {contract['frozen_at']}, pelos horários do catálogo local, **69 jogos
tinham a decisão T−1h no passado e 121 tinham essa decisão no futuro**. Isso não é
uma contagem de partidas com resultado confirmado; nenhum placar foi consultado.

Os 69 podem entrar como replay histórico exploratório. Os 121 podem receber
registros prospectivos se previsão, preço e regra forem registrados a tempo.
Eles permanecem NO_BET neste manifesto inicial porque nenhum candidato foi
promovido. Mudar a divisão não torna lucrativa a hipótese que falhou nos 51 jogos.
Horários futuros são metadados operacionais e precisam ser atualizados antes
de cada decisão; nenhuma data da tabela básica foi usada como horário definitivo.

## Identidade e qualidade dos dados

Os 386 cadastros locais de 2026 foram relacionados aos 380 confrontos oficiais.
Cinco registros já possuíam substituição explícita. O sexto caso era Botafogo ×
Grêmio: o [jogo 202 da CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-a/2026/botafogo-x-gremio/832091?view=escalacao)
está marcado para 16/09/2026, às 19h30 de Brasília, pela rodada 21. O manifesto
usa o ID local que corresponde a essa data e mantém o antigo como referência,
sem contá-lo duas vezes. Nenhuma linha do banco foi alterada.

O histórico de treino/calibração reutiliza a versão já verificada de 1.900
eventos de 2021–2025. A contagem bruta de linhas do banco inclui cadastros extras
e não foi usada como tamanho da amostra de treino.

## Alcance da mudança

Foi acrescentado ao projeto um contrato de divisão, o manifesto dos 380 jogos,
a fonte histórica identificada por hash e um classificador de simulação. O
classificador preserva a rodada mesmo após adiamentos e usa a decisão T−1h para
separar replay de registro futuro. Ele não calcula apostas nem executa ordens.
Nenhum agendador ou avaliador legado foi redirecionado automaticamente.

2025 e parte de 2026 já foram examinados em análises anteriores. Esta organização
não transforma o primeiro turno em teste cego nem apaga estudos encerrados.
Nesta nova divisão, o primeiro turno serve para testar, não para reajustar o
modelo; o segundo não será usado para selecionar parâmetros retrospectivamente.
H14/H15/H9/A1 mantêm seus protocolos e resultados separados.

Verificação: **110 testes aprovados**, Ruff aprovado e 14 hashes de arquivos
protegidos preservados. Não houve novo cálculo de resultado de apostas ou lucro.

[Contrato aplicado](contrato.json) · [380 jogos e seus grupos](jogos_2026.json) ·
[Partição do histórico](particao_historica.json) · [Testes](testes.txt) ·
[Integridade](integridade.json)
"""
(OUT/'DIVISAO.md').write_text(report,encoding='utf-8')
checkpoint = """## CHECKPOINT — DIVISÃO POR TURNOS DE 2026 APLICADA (2026-09-07)

Pedido do operador: primeiro turno de2026 como teste e segundo turno inteiro como
universo para apostar; execução interpretada e comunicada como simulação/paper.
Escolha restante:2021–2024treino(1520jogos),2025calibração(380), usando snapshot
histórico previamente verificado por hash. Rodadas1–19testeexploratório(190) e
20–38paper(190), via tabela oficial CBF, nunca semestre ou cronologia de confrontos.

Contrato contracts/season-2026-turn-split-paper.json; manifesto/fonte histórica
em data/research/season_2026_turn_split; módulo research/season_2026_split.py.
380confrontos/380IDs canônicos;6cadastros extras não duplicamjogos. Botafogo×Grêmio
reconciliado por data oficial CBF16/09 às19h30(rodada21), semeditarobanco.

No congelamento,69decisõesT−1hdo2Tjápassaram e121eramfuturas pelosmetadados.
Passado sóreplayexploratório, futuro sópapersignalcomgatesPIT. Universo190nãoé
obrigação190apostas. Nenhumcandidato promovido, capitalfalse, apostaszero.
110testes eRuff aprovados;14hashesprotegidos iguais. Nenhumresultado2026oucoorte
protegidaavaliado. Nenhumagendador/runnerlegadoredirecionado. Esta divisão é
para novasavaliações, preserva estudos anteriores e dívida exploratória.
Entregas: Documents/Codex/2026-09-07/le/outputs/DIVISAO_2026/DIVISAO.md.
"""
handoff = REPO/'HANDOFF.md'
body = handoff.read_text(encoding='utf-8-sig')
assert checkpoint.splitlines()[0] not in body
first, rest = body.split('\n',1)
quoted = '\n'.join('> '+line if line else '>' for line in checkpoint.splitlines())
handoff.write_text(first+'\n\n'+quoted+'\n'+rest,encoding='utf-8')
(OUT/'CHECKPOINT_FINAL.md').write_text(checkpoint,encoding='utf-8')
with zipfile.ZipFile(OUT/'divisao_aplicada.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in OUT.iterdir():
        if path.is_file() and path.suffix!='.zip':
            archive.write(path,path.name)
with zipfile.ZipFile(OUT/'divisao_aplicada.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'report':str(OUT/'DIVISAO.md'),'contract_sha256':sha(CONTRACT),'canonical_2026_fixtures':380,'train':1520,'calibration':380,'protected_hashes_verified':14}))
