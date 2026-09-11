# Decisões do delta

## N01

Baseline: Grade NB/DC fixa em 12; renormalização oculta massa omitida.

Referência: Cauda NB por survival function; referência ampliada certificada; baseline extraída.

Resultado: `{"case_count": 147, "maximum_market_error": 9.382467890395318e-07, "maximum_candidate_tail": 9.941970383213497e-07, "support_min": 5, "support_max": 79, "maximum_reference_tail": 2.0617257199979766e-13, "median_baseline_seconds": 0.0007063999946694821, "median_candidate_seconds": 0.01674930000444874}`

Decisão: Conservar diagnóstico e protótipo; corrigir custo e validar domínio completo em pesquisa antes de revisão de integração.

Limitação: Domínio de pesquisa alpha [0.01,2] não cobre fitter operacional [0.0001,3]. Mediana de custo aproximadamente 23.7 vezes maior; não é benchmark estável de produção.

Próximo gate: Cobertura dos limites operacionais, orçamento de latência e revisão de chamadas/mercados condicionais.

Artefatos: [research/adaptive_goals.py](research/adaptive_goals.py), [research/test_n01.py](research/test_n01.py), [evidence/N01.json](evidence/N01.json)

## N02

Baseline: Funções de margem com regimes e falhas pouco explícitos; métricas existentes em tensor.

Referência: Funções locais e segmentos penaltyblog fixados; identidades analíticas.

Resultado: `{"status": "PASS", "comparisons": 14, "score_cases": 4, "invalid_odds": 10, "invalid_external_outputs": 6}`

Decisão: Merece revisão do contrato para futura integração; manter implementação isolada.

Limitação: Concordância matemática não comprova odds contemporâneas nem calibração empírica. Bibliotecas completas não executadas.

Próximo gate: Revisão da API, chamadores e semântica de mercados reais completos.

Artefatos: [research/strict_math.py](research/strict_math.py), [research/test_n02.py](research/test_n02.py), [evidence/N02.json](evidence/N02.json)

## N03

Baseline: Curadoria/closing/PIT têm escopos distintos; alguns registros aceitos não são admissíveis ao cutoff de decisão.

Referência: Contratos locais extraídos e fixtures sintéticas identificadas.

Resultado: `{"adapter_cases": 18, "baseline_assertions": 15, "mutants": 15, "killed": 15, "survived": [], "invalid_mutants": 0}`

Decisão: Conservar suite e adapter de pesquisa; tratar lacunas como escopo de admissão, sem declarar defeito global.

Limitação: 15 mutantes detectados não representam 15 perdas independentes de segurança: M04 muda somente motivo de recusa; M02 altera vintage/status. Autenticidade e mercado completo não cobertos.

Próximo gate: Completar admissão conjunta 1X2 e evidência de identidade/relógios reais.

Artefatos: [research/strict_pit.py](research/strict_pit.py), [research/test_n03.py](research/test_n03.py), [evidence/N03.json](evidence/N03.json), [evidence/N03-mutation-audit.json](evidence/N03-mutation-audit.json)

## N04

Baseline: Coordenadas/xT toy eram opção habilitadora.

Referência: Prioridade e dependências do mandato.

Resultado: `{"status": "DEFERRED"}`

Decisão: Adiar; não duplicar descanso/contexto existentes.

Limitação: Não resolve o bloqueio atual de odds e linhagem.

Próximo gate: Questão concreta de transferência e fonte admissível.

Artefatos: 

## N05

Baseline: Comparação preditiva não liberada; existe sobreposição conceitual com BE.

Referência: Contratos e metadados permitidos; nenhum avaliador ou arquivo de resultados aberto.

Resultado: `{"A": "BLOCKED", "B": "BLOCKED", "fitting_executed": false}`

Decisão: Não executar fitting nem consultar desfechos para decidir viabilidade.

Limitação: Sem manifesto de coorte autorizado, revisão de interseções e odds T−60 admissíveis. Aceite pessoal não é gate de A.

Próximo gate: Manifesto imutável aprovado, resolução de linhagem e auditoria de clocks/odds/histórico.

Artefatos: [N05_PROTOCOL.json](N05_PROTOCOL.json), [N05_DATA_CONTRACT.json](N05_DATA_CONTRACT.json), [N05_PROTOCOL.md](N05_PROTOCOL.md)

Estados separados: {"ENGINEERING_STATUS": "SYNTHETIC_TESTS_PASSED_WITH_LIMITATIONS", "DATA_ADMISSIBILITY": "NO_REAL_COHORT_ADMITTED", "PREDICTIVE_EVIDENCE": "NONE_THIS_RUN", "ECONOMIC_EVIDENCE": "NONE_THIS_RUN"}
