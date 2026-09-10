# Notas finais de verificação CLO

Regressões Python anteriores: before32 falhas/1 passagem, coverage-before2 falhas, status-before1, research-before16. Depois, integrated-final275 passagens, sem falhas/skips. Guard bloqueou uma tentativa socket.bind antes de acesso; nenhuma tentativa de SQLite operacional no lote final após retirar o CLV automático.

Ruff/Pyright primeiro encontraram linhas longas e acesso Optional no teste; falhas preservadas em quality-first. Correções sem exclusões/tolerâncias novas. Última verificação14 arquivos Python, zero erros/avisos. Testes antigos de readiness atualizados para a versão2, que retira selo oficial; teste de closing ganhou contexto de fonte/evento/período/status exigido pela versão2.

.NET: runtime119/119; latency-before119 passagens e6 novas regressões falharam; latency-after127/127. Os3 testes de configuração de budget foram movidos para classe sem fixture Redis porque não precisam de conexão; as3 mesmas entradas inválidas continuam testadas. Dois testes adicionais verificam CAS obsoleto e revisão com clocks inválidos. Namespace de estatísticasv2 preserva o v1. Não foram aumentados timeouts para fazer testes passar. Falha de bootstrap anterior permanece no checkpoint CPL; causa ainda desconhecida.

Pacote: wheel e sdist offline, instalação com --python apontado explicitamente ao RI. Sete comandos e validação de saídas/códigos de retorno. Nenhuma autodetecção de outro projeto nesta etapa. A wheel contém Python e scripts; .NET é fonte/bundle com build/test isolado comprovado. Notas, manifestos e recibo final são produzidos depois do build e entregues separadamente; não alegar que estão dentro do sdist.

Automação: ferramenta view antes retornou apenas cartão. Tentativa somente leitura do TOML esperado não encontrou arquivo; isso não prova que o heartbeat do aplicativo foi removido ou esteja inativo. Nenhum agendamento alterado/duplicado. A execução futura só pode ser afirmada com recibo e estado apropriados.

O primeiro preparo do índice enumerava apenas arquivos não ignorados e deixava35 logs fora do Git, embora presentes na pasta e no manifesto. Antes do commit, a enumeração passou a incluir todos os arquivos desta entrega; cada recibo foi conferido byte a byte contra o índice. A regra global que ignora logs não foi alterada.

Esta é uma integração de continuidade, com mandato_complete=false. Sem novas métricas de mercado, preços, labels ou operações financeiras. Campos de retencão/latência são diagnóstico técnico. JSON/XML/logs de máquinas são preservados byte a byte; o .gitattributes local permite o espaço bruto do runner e evita normalização desses recibos.
