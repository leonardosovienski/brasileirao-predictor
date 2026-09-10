# Reprodução delimitada

Todos os caminhos são C:/BRASILEIRAO. Python 3.13.12/extras em work/revisao-integral-2026-09-09/venv; SDK .NET 10.0.401 e NuGet no mesmo workspace; Redis 8.2.9 portátil em work/implementacao-2026-09-10/software. Dependências verificadas na RCA não equivalem a serviços ativos. O launcher run_isolated.py limpa ambiente, bloqueia rede/subprocessos e escritas fora de nova saída, DBs/coortes/config privados; não usar pytest global.

Casos e nomes exatos das 10 suítes estão em evidence/python-validation.json e isolation.json correspondentes. Execute somente allowlist revisada em diretório novo pelo runner, com -I -B. Runners e comandos completos: C:/BRASILEIRAO/work/resolution-2026-09-10. O laboratório .NET exige porta 26380 livre antes de iniciar seu próprio Redis e verifica PID/run_id/SHA; limpa somente o processo próprio. O recibo guarda restore/build/test e tempos, não são medidas de latência de produção.

A wheel final é derivada do sdist offline e instalada em venv separado sem PYTHONPATH, com reutilização explícita das dependências isoladas já verificadas. Isso não representa reinstalação independente da cadeia inteira. Recibo package-final-02/receipt.json e installed-cross-final/receipt.json descrevem resultados reais. Build/CLI help/health usam dados sintéticos. Não executar CLI de coleta, backfill ou settlement em caminhos operacionais.
