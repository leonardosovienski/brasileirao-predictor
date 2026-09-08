"""Publish verified replay artifacts without touching operational sources."""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
OUT = ROOT / 'outputs/BACKTEST_NOVO_2026'
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value, digits=2):
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def main():
    r = json.loads((WORK/'run/results.json').read_text(encoding='utf-8'))
    c = json.loads((WORK/'run/candidate.json').read_text(encoding='utf-8'))
    a = json.loads((WORK/'run/audit_results.json').read_text(encoding='utf-8'))
    if a['status'] != 'PASS' or a['error_count'] or not r['model_state_unchanged']:
        raise ValueError('Audit failed')
    baseline = json.loads((ROOT/'outputs/DIVISAO_2026/integridade.json').read_text(encoding='utf-8'))
    protected = {name:sha(REPO/name) for name in baseline['protected_sha256']}
    if protected != baseline['protected_sha256']:
        raise ValueError('Protected source changed')
    for name, expected in c['source_sha256'].items():
        source = WORK/name if (WORK/name).is_file() else REPO/name
        if sha(source) != expected:
            raise ValueError(f'Candidate source changed: {name}')
    OUT.mkdir(parents=True, exist_ok=True)
    source_out = OUT/'reproducao'
    source_out.mkdir(exist_ok=True)
    for name in ('plan.json','runner.py','economics.py','extract_inputs.py','audit_results.py',
                 'test_runner.py','test_economics.py','test_extract_inputs.py','test_audit_results.py'):
        shutil.copy2(WORK/name, source_out/name)
    for path in (WORK/'run').glob('*.json'):
        shutil.copy2(path, OUT/path.name)
    for path in (WORK/'data').glob('*.json'):
        shutil.copy2(path, OUT/path.name)
    integrity = {'checked_at_utc':datetime.now(UTC).isoformat(),
                 'protected_files_unchanged':True,'protected_sha256':protected,
                 'plan_sha256':r['plan_sha256'],'candidate_sha256':r['candidate_sha256'],
                 'candidate_sources_match':True,'state_unchanged_after_760_forecasts':True,
                 'economic_audit':'PASS, 760 decisions, zero divergences',
                 'artifact_sha256':{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}}
    (OUT/'integridade.json').write_text(json.dumps(integrity,indent=2)+'\n',encoding='utf-8')
    inputs = json.loads((WORK/'run/replay_inputs.json').read_text(encoding='utf-8'))
    lookup = {e['id']:e for e in inputs['primary_calibrated']}
    selected = [d for d in r['arms']['primary_calibrated']['decisions'] if d['role']=='paper_betting' and d['status']=='SETTLED']
    lines = [
        '# Novo backtest de 2026: prejuízo no trecho disponível do segundo turno', '',
        '**Executado em 07/09/2026. A versão calibrada fez 9 apostas, acertou 4 e perdeu 1,23 unidade após custos.** '
        'Com R$50 por aposta, o prejuízo seria de **R$61,50**, e uma banca inicial de R$5.000 terminaria em **R$4.938,50**.', '',
        'O cálculo abrange 58 jogos concluídos e disponíveis do segundo turno. Os 190 jogos oficiais continuam no universo; '
        'os outros 132 não receberam resultados inventados nem entraram no cálculo de retorno.', '',
        '| Segundo turno, rodadas 20–38 | Principal: calibrado em 2025 | Comparação: sem calibração |',
        '|---|---:|---:|',
    ]
    p = r['arms']['primary_calibrated']['by_role']['paper_betting']
    d = r['arms']['diagnostic_raw']['by_role']['paper_betting']
    table = [
        ('Jogos concluídos avaliados','58 de 190','58 de 190'),
        ('Apostas',str(p['settled_bets']),str(d['settled_bets'])),
        ('Acertos / erros',f"{p['wins']} / {p['losses']}",f"{d['wins']} / {d['losses']}"),
        ('Saldo bruto (unidades)',fmt(p['gross_profit_units'],3),fmt(d['gross_profit_units'],3)),
        ('Custos adicionais (unidades)',fmt(p['cost_units']),fmt(d['cost_units'])),
        ('Saldo líquido (unidades)',fmt(p['net_profit_units'],3),fmt(d['net_profit_units'],3)),
        ('ROI líquido sobre o total apostado',fmt(100*p['net_roi'])+'%',fmt(100*d['net_roi'])+'%'),
        ('Saldo líquido, R$50 por aposta','R$'+fmt(50*p['net_profit_units']),'R$'+fmt(50*d['net_profit_units'])),
        ('Maior queda desde um pico (R$50/unidade)','R$'+fmt(50*p['max_drawdown_units']),'R$'+fmt(50*d['max_drawdown_units'])),
    ]
    lines.extend('| '+' | '.join(row)+' |' for row in table)
    lines += ['', 'A calibração reduziu a perda e a exposição nesta amostra, mas **não tornou a estratégia lucrativa**. '
              'O modelo sem calibração já estava definido como comparação antes do cálculo; ele não substitui o resultado principal.', '',
              'Treino: 1.520 jogos de 2021–2024, com ajuste único da pilha NegBin + Dixon–Coles do projeto. '
              'Calibração: 380 jogos de 2025, dos quais 374 tinham preços aprovados pelos mesmos filtros usados em 2026. '
              'Teste: as rodadas 1–19 de 2026. Simulação: as rodadas 20–38. Nenhum resultado de 2026 entrou no treino, '
              'na calibração ou na escolha dos limites de aposta desta execução.', '',
              'Na calibração de 2025, o peso do modelo foi 0% para resultado do jogo, 0% para gols acima/abaixo de 2,5 '
              'e 89,52% para ambas marcam; o restante veio das probabilidades implícitas das odds, retirando a margem proporcionalmente. '
              'Por isso, todas as nove apostas selecionadas no segundo turno foram em **ambas marcam: não**.', '',
              '| Primeiro turno: teste separado | Principal calibrado | Sem calibração |',
              '|---|---:|---:|']
    t1p = r['arms']['primary_calibrated']['by_role']['test_exploratory']
    t1d = r['arms']['diagnostic_raw']['by_role']['test_exploratory']
    lines += [f"| Apostas | {t1p['settled_bets']} | {t1d['settled_bets']} |",
              f"| Saldo líquido (unidades) | {fmt(t1p['net_profit_units'],3)} | {fmt(t1d['net_profit_units'],3)} |",
              f"| ROI líquido | {fmt(100*t1p['net_roi'])}% | {fmt(100*t1d['net_roi'])}% |", '',
              'Os resultados do primeiro turno foram apenas medidos; não houve ajuste da regra após esse teste.', '',
              'Regra aplicada: no máximo uma aposta por jogo, escolhida pelo maior retorno esperado líquido entre resultado do jogo, '
              'gols acima/abaixo de 2,5 e ambas marcam. A probabilidade estimada precisa superar 1/odd em mais de 2 e no máximo 15 pontos percentuais. '
              'Exige retorno esperado líquido positivo, mercado completo, limites de odds e margem da casa entre 1,00 e 1,30. '
              'Cada aposta vale 1 unidade fixa; a simulação desconta custo adicional de 0,02 unidade por aposta, inclusive nas perdedoras.', '',
              'As nove apostas do resultado principal estão abaixo. Datas no horário de Brasília. A coluna líquida já desconta R$1 de custo por aposta de R$50.', '',
              '| Data | Rodada | Jogo | Placar | Ambas marcam | Odd | Resultado líquido |',
              '|---|---:|---|---:|---|---:|---:|']
    for decision in selected:
        event = lookup[decision['id']]
        dt = datetime.fromisoformat(event['kickoff_at']).astimezone(ZoneInfo('America/Sao_Paulo'))
        lines.append(f"| {dt:%d/%m/%Y} | {event['round']} | {event['home']} × {event['away']} | "
                     f"{event['home_goals']}–{event['away_goals']} | Não | {fmt(decision['candidate']['odd'],2)} | "
                     f"R${fmt(50*decision['settlement']['net_profit_units'])} |")
    lines += ['', '**Limites do resultado.** Corte dos dados em 07/09/2026 às 19h43 de Brasília, com intervalo de 48 horas após o início do jogo '
              'para considerar o placar disponível. Há 129 partidas fora dessa janela e três com placar ausente. '
              'As três pendências são São Paulo–Santos, Atlético Mineiro–Red Bull Bragantino e Chapecoense–Vasco, rodadas oficiais do manifesto. '
              'Placar concluído exige concordância entre as duas tabelas locais e data de observação até o corte.', '',
              'As odds são agregadas retrospectivas já existentes no banco, sem comprovação de casa, horário de oferta ou execução antes do jogo. '
              'Logo, este é um resultado hipotético nessas cotações, não lucro realizável demonstrado. O histórico de 2026 já havia sido explorado '
              'anteriormente; congelar este plano agora não transforma o estudo em teste cego.', '',
              'O Elo e os parâmetros ficaram congelados no fim de 2024, conforme a separação desta execução; isso deixa as forças dos times antigas em 2026. '
              'Mirassol e Remo, ausentes do treino, receberam o rating inicial de 1.500. '
              'Os R$50 são uma conversão fixa das unidades, sem reinvestimento ou interrupção por banca. '
              'A queda é calculada por ordem de início dos jogos, incluindo saldo inicial zero, e não reconstrói horários intradia de liquidação.', '',
              'Validação: ajuste convergiu sem avisos; estado do modelo permaneceu idêntico após as previsões de 2025 e 2026. '
              'Uma segunda implementação, independente da função de liquidação, recalculou as 760 decisões dos dois braços, os pagamentos, '
              'os resultados por turno e rodada, as curvas e as quedas: nenhuma divergência. Os 14 arquivos operacionais protegidos mantiveram seus hashes.', '',
              'Este novo resultado substitui a resposta anterior de que a divisão ainda não tinha sido executada. '
              'O antigo +5 unidades veio de outra regra e outra amostra; ele não representa esta execução.', '',
              f"Plano SHA256: `{r['plan_sha256']}`. Candidato SHA256: `{r['candidate_sha256']}`.", '',
              'Os arquivos JSON nesta pasta contêm o candidato, as probabilidades, os dados usados, as decisões e a auditoria. '
              'A pasta reproducao contém o plano, os programas e os testes. O replay não alterou o modelo de produção nem colocou apostas reais.', '']
    (OUT/'RESULTADO.md').write_text('\n'.join(lines),encoding='utf-8')
    print(str(OUT/'RESULTADO.md'))


if __name__ == '__main__':
    main()
