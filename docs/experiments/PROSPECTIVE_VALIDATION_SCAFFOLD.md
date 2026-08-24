# Pipeline de validação prospectiva — scaffold

Estado: `PAPER_TRADING_ONLY`.

O pipeline registra picks imutáveis com horário de previsão, kickoff, horário e
preço capturado, bookmaker, probabilidade e stake flat fixa de 1 unidade. A
liquidação preserva odd de fechamento pré-kickoff, timestamp, resultado e fonte.

As métricas declaradas são CLV logarítmico médio, ROI flat com IC95 bootstrap,
calibração binária, coverage, PSR, DSR e power analysis parametrizado pela odd
média observada no nicho. O gate de DSR é `>=0,95` e nunca libera capital.

As únicas saídas possíveis são:

- `CAPITAL_GATE: LOCKED`;
- `CAPITAL_GATE: ELIGIBLE_FOR_REVIEW`.

`ELIGIBLE_FOR_REVIEW` significa apenas que a coorte pode ser examinada por uma
pessoa. A decisão de capital é humana e não existe função de aposta, stake real,
Kelly, transferência ou habilitação de banca neste pacote.
