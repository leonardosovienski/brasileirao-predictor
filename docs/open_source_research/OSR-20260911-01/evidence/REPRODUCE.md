# Reprodutibilidade dos ensaios

Este diretório preserva o harness efetivamente executado, suas entradas, resultado e módulos copiados com hashes. Não execute o pacote operacional ou pytest global. A licença MIT de penaltyblog acompanha seus dois arquivos; módulos internos são cópias para revisão do próprio projeto, não nova licença de redistribuição pública.

Para uma reprodução futura, criar diretório novo separado, copiar este diretório para lá e **preservar o resultado original como arquivo de referência com outro nome**; o harness usa criação exclusiva de benchmark_results.json para não sobrescrever resultados. Criar venv Python 3.13.12 e instalar somente requirements.txt com wheels. A execução original foi python -I -B benchmark.py. Não incluímos a venv ou credenciais.

Antes de executar novamente: sanitizar ambiente do processo, impor timeout de 120 segundos e estabelecer sandbox de OS sem rede/stores privados. O audit hook do harness é proteção limitada, não substitui essas condições. A reprodução com isolamento reforçado será nova execução registrada; não foi realizada nesta rodada. Nenhum script automático de instalação/reprodução é fornecido para disparar ações ao abrir os documentos.

O tempo de 0,268 s não é comparação de desempenho; diferenças de CPU ou startup impedem extrapolação. Os hashes de módulo do resultado verificam identidade das cópias originais, não eficácia estatística.
