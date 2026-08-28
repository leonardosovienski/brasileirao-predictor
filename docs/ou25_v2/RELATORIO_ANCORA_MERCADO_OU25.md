# Implementação da âncora de mercado OU2.5

## O que foi alterado

A probabilidade esportiva passou a poder ser encolhida em direção ao mercado
OU2.5 de-vigado. O peso do modelo é escolhido entre `{0, 0,25, 0,50, 0,75, 1}`
usando somente o prefixo temporal anterior e permanece congelado durante o
bloco seguinte de 38 jogos.

`peso=0` significa mercado puro; `peso=1` significa modelo puro. Labels futuros
não participam da escolha. O mecanismo foi coberto por teste contrafactual.

## Resultado prequential

Painel avaliado: 750 jogos.

| Probabilidade | Brier |
|---|---:|
| Modelo esportivo | 0,246397 |
| Modelo ancorado | **0,242527** |
| Mercado de-vigado | **0,242146** |

A âncora reduziu o erro do modelo em aproximadamente 1,57%, mas não venceu o
mercado. Na maioria dos folds o peso escolhido foi zero; quatro folds antigos
selecionaram peso 0,25. Nenhum fold selecionou peso 0,50, 0,75 ou 1,00.

## Resultado econômico

Após a âncora, o replay aninhado com 1.620 combinações por fold gerou zero
recomendações externas. Apostar sempre no maior EV aparente perdeu 14,32% no
recorte de 2023. Portanto a melhora é de calibração e segurança: ela remove
falsos edges, mas não demonstra vantagem econômica.

## Decisão

- melhoria probabilística: **SIM**;
- superior ao mercado: **NÃO**;
- filtro econômico aprovado: **NÃO**;
- recomendação atual: **NO_BET**;
- capital: **desabilitado**;
- força máxima sem A1: **40/100**.

A âncora não foi ligada ao serving operacional porque as odds usadas são
retrospectivas e não possuem timestamp/casa executável. O código está pronto
para receber snapshots PIT prospectivos quando o coletor A1 produzir uma fonte
homologada.
