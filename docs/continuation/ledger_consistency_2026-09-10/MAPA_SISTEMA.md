# Mapa vigente LGC

O [mapa CLO](../closeout_2026-09-10/MAPA_SISTEMA.md) mantém os demais subsistemas e limites. LGC substitui somente o estado de bet_log: CLI/manual → JSONL de apostas e banca → lista, liquidação e resumo brutos. Não é um executor financeiro.

| Componente | Dependência/consumidor | Decisão e prova |
| --- | --- | --- |
| _writer_lock / _single_writer | OS local; add/settle/bank_init/bank_flow | Corrigir: msvcrt Windows/fcntl POSIX, sidecar estável, erro imediato em conflito. Windows comprovado em threads/processos; POSIX não executado. |
| _append / _read_records | JSONL UTF-8; todos os consumidores manuais | Corrigir: LF se necessário sem alterar bytes antigos, flush/fsync, JSON estrito; corrupção recusa leitura. |
| bank_state | Snapshot bancário + um snapshot de apostas | Corrigir mistura de snapshots de apostas; escopo bruto e drawdown limitado explícitos. Sem transação entre os dois livros. |
| _settlement_index / settle_bet | MARKETS, _canon protegido e inalterado | Corrigir contratos/IDs/mando; preservar registros históricos e relatos como não autenticados. |
| main | Consumidor CLI | Retirar certificação indevida de CLV/mercado. validated mantido somente por compatibilidade. |

A contagem cumulativa em evidence/source-inventory.json preserva categorias e hashes anteriores, atualizando somente as fontes lidas/modificadas nesta etapa. A cobertura global permanece parcial. O arquivo protegido math_utils e os demais contratos H14/H15/H9/A1 não foram alterados. Não instalar nem executar operações protegidas para completar uma contagem.
