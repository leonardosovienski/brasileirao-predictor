from pathlib import Path

p=Path('C:/BRASILEIRAO/brasileirao-predictor/brasileirao_scripts/odds_shop.py')
s=p.read_text(encoding='utf-8')
end=s.index('"""',3)+3
s='''"""Descriptive bookmaker price comparison for Brasileirão.

The display validates complete prices and optional age limits. It does not
authenticate bookmaker availability, model calibration, costs or accepted fills.
Saved responses are locally received observations, not source publication clocks.
The legacy model comparison is diagnostic and cannot authorize capital.

Use --from-file for offline inspection. Network acquisition requires a separately
verified plan, quota and reserve; this legacy CLI does not establish that budget.
"""'''+s[end:]
start=s.index('# Sport key')
end=s.index('_quota =',start)
s=s[:start]+'''# Importing this diagnostic must not read operational configuration.
SPORT = "soccer_brazil_campeonato"
MIN_EDGE_DEFAULT = 0.03
MIN_BOOKS = 4

'''+s[end:]
start=s.index('                # JANELA VALIDADA')
end=s.index('        if tempos_key:',start)
s=s[:start]+s[end:]
start=s.index('    """Odds de 1T/2T')
end=s.index('    data = fetch_period_odds',start)
s=s[:start]+'''    """Display period-price diagnostics without a betting recommendation."""
'''+s[end:]
start=s.index('                        mk_code =')
end=s.index('                print(',start)
s=s[:start]+'''                        marker = f"diferenca vs modelo {edge_best:+.1%} (diagnostico)"
'''+s[end:]
start=s.index('    print(f"\\nRegras aplicadas:')
end=s.index('    if _quota["remaining"]',start)
s=s[:start]+'''    print(f"\\nLimiar de exibicao das diferencas: {min_edge:.0%}.")
    print("Comparacao descritiva: custos, aceitacao e lucro executavel nao foram validados.")
    print("Capital permanece desabilitado; probabilidades do cache legado sao diagnosticas.")
'''+s[end:]
s=s.replace('# snapshot auditavel (published_at da informacao)', '# Snapshot local recebido; published_at da fonte permanece desconhecido.')
s=s.replace('except Exception as e:\n            print(f"falha na API de odds: {e}")', 'except Exception:\n            print("falha na API de odds: fonte indisponivel")')
s=s.replace('default=15.0,\n        help=', 'default=15.0,\n        help=')
s=s.replace('"0 desliga. So vale no modo online; --from-file nunca "', '"Exige valor positivo no modo online; --from-file nunca "')
s=s.replace('    args = ap.parse_args()\n', '''    args = ap.parse_args()
    if not math.isfinite(args.min_edge) or not 0 <= args.min_edge <= 1:
        ap.error("--min-edge deve estar entre 0 e 1")
    if not args.from_file and (not math.isfinite(args.max_stale_min) or args.max_stale_min <= 0):
        ap.error("--max-stale-min deve ser finito e positivo")
    if args.from_file and args.tempos:
        ap.error("--from-file nao permite consultas de rede com --tempos")
''')
s=s.replace('                "  3. Rode de novo (na rede limpa — a Volvo bloqueia)."', '                "  3. Confira plano, quota e reservas antes de qualquer coleta."')
p.write_text(s,encoding='utf-8')
