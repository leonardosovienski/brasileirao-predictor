# Motor de backtest live — BLOQUEADO

Estado: `HOLD_NO_LIVE_VIABILITY_GO`.

Este arquivo é apenas um placeholder de governança. O Gate L0 documental foi
concluído em `LIVE_FEASIBILITY_01.md` e confirmou o HOLD: nenhuma combinação
comprovou simultaneamente coverage histórica da Série A, replay executável e
custo dentro do teto pessoal. Nenhum motor live foi implementado.

## Condições para desbloqueio

O trabalho só pode começar após uma evidência imutável confirmar:

1. feed histórico de eventos com timestamps reais e cobertura adequada do
   Brasileirão;
2. odds live históricas por mercado e timestamp, incluindo margem real;
3. registro de suspensões, reaberturas e mudanças de preço;
4. custo do feed e operação compatível com o bankroll;
5. regras point-in-time suficientes para um backtest sem lookahead.

## Contrato obrigatório da futura implementação

Caso a viabilidade receba GO, o motor deverá simular minuto a minuto:

- placar, minuto e cartões conhecidos naquele instante;
- atualização de probabilidades usando somente o estado disponível;
- margem live observada no timestamp correspondente;
- delay de envio e aceitação da ordem;
- suspensão e reabertura do mercado durante o delay;
- preço efetivamente disponível no instante de aceitação, não o preço visto
  antes do envio;
- rejeições, apostas não aceitas e custo de execução.

Um backtest live sem delay de aceitação, suspensão de mercado e custo de
execução simulado é inválido por construção. A futura API deverá falhar
explicitamente quando qualquer um desses componentes estiver ausente; não será
permitido assumir custo zero ou aceitação instantânea como default.

## Fora de escopo enquanto HOLD

Não criar runner, classes de estado live, atualização probabilística, fixtures
sintéticos, backtest diagnóstico ou integração com serving. Este placeholder
não constitui pré-registro, GO, autorização de coleta ou autorização de
capital.
