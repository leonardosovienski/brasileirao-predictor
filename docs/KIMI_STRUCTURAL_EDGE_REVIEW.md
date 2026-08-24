# Revisão da proposta externa de edge estrutural

## Aceito e integrado

- O pivot conceitual de modelo-versus-mercado para referência sem vig versus
  casa soft foi registrado como MARKET-05.
- Métodos Shin e power, threshold de EV de 3% e staleness de 300 segundos.
- Validação forte de evento, mercado, linha, seleção, mapping, timezone e
  cutoff pré-kickoff.
- Apenas candidato shadow, compatível com o ledger prospectivo já governado.

## Não copiado

O `PaperLedger` externo regravava o arquivo inteiro apesar da alegação de
imutabilidade, usava `assert` como controle de segurança e não protegia
timezone, identidade, linha ou duplicatas. O cálculo DSR paralelo também
criaria duas fontes de verdade. O projeto preserva seu ledger append-only e
suas métricas existentes.

## Bloqueado ou rejeitado

- Coleta e claims de cobertura: não havia dados auditáveis no ZIP.
- Arbitragem, promoções, execução e capital real: fora do protocolo científico
  e incompatíveis com o gate humano obrigatório.
- Táticas de evasão de limitação de conta: rejeitadas e não implementadas.
- Motor live: continua HOLD; MARKET-05 não altera o gate da Fase 2.

Nenhum backtest, treino ou validação econômica foi executado nesta integração.
