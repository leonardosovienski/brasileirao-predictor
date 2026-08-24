# Structural edge shadow protocol — MARKET-05

## Hipótese ex ante

Uma probabilidade de referência obtida de um mercado Pinnacle completo e sem
vig pode identificar divergências reproduzíveis em uma casa soft nomeada. A
hipótese é apenas candidata: nenhum resultado sintético ou alerta isolado é
evidência econômica.

## Política congelada

- Referência: `pinnacle`, com método Shin primário e power apenas como análise
  de sensibilidade.
- Alerta: `EV = p_fair * odd_soft - 1 > 0,03`.
- Staleness máxima da referência: 300 segundos.
- Event ID, mercado, linha, versão do mapping, kickoff e conjunto de seleções
  devem coincidir. Timestamp deve ter timezone e toda informação deve existir
  estritamente antes do kickoff.
- Saída exclusiva: `PAPER_CANDIDATE`, `SHADOW_ONLY` e
  `CAPITAL_GATE: LOCKED`.

## Gate antes de qualquer avaliação econômica

O coletor ainda não existe. Exigir no mínimo cinco casas brasileiras nomeadas,
sete dias consecutivos, cobertura PIT auditável >= 90%, auditoria humana de 50
matches de identidade/linha e snapshots append-only. Depois disso, registrar
um protocolo prospectivo novo antes de observar ROI, CLV, PSR ou DSR. O DSR
continua no pipeline governado existente e não foi duplicado neste módulo.

## Fora de escopo

Não há scraping, automação de conta, execução de aposta, arbitragem, promoção,
stake, evasão de limite nem orientação de capital real. O motor live continua
bloqueado pelo gate da Fase 2.
