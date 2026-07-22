# Definição de closing line

A closing line do backfill PIT é a última cotação válida, por bookmaker, mercado e seleção, capturada antes do `kickoff_at`. A cotação precisa ter `odds_captured_at <= kickoff_at`, ser finita e maior que 1.0, e estar dentro da janela de 72 horas por padrão.

O resultado é versionado como `closing-v1:last-valid-pre-kickoff-by-bookmaker`. Cotações posteriores ao início da partida são rejeitadas, não corrigidas silenciosamente. Se não houver cotação elegível, o registro permanece sem closing line e não entra em métricas que exigem esse campo.
