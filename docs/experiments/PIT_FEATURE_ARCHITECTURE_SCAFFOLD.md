# Arquitetura de informação PIT — scaffold

Estado: `SCAFFOLD_ONLY_TRAINING_BLOCKED`.

Este pacote define contratos para desfalques, escalações, uma arquitetura xG
isolada e mando por equipe com shrinkage hierárquico. Não contém fitting,
estimadores, backtest, seleção de hiperparâmetros ou integração com serving.

Cada família declara antes do treino o mecanismo, os campos exigidos, a saída
pretendida e a política de proveniência. Toda evidência preserva quatro relógios
UTC: observação, disponibilidade pública real, ingestão e kickoff. A informação
só é elegível quando `available_at < kickoff_at`; igualdade também falha.
Ingestão tardia não permite retroagir `available_at`.

O xG pertence à linhagem `ISOLATED_XG_NEW_LINEAGE`. Reuso do ensemble H12,
blend de probabilidades ou de grades com o serving são proibidos.

Treino permanece bloqueado até Fase 0B ou viabilidade live produzir GO com uma
referência imutável de evidência. O gate não autoriza capital nem promoção.
