"""Em redes corporativas com inspeção TLS (proxy que troca o certificado),
o truststore faz o Python confiar no mesmo cofre de certificados do SO —
sem desabilitar verificação. Carrega aqui, antes de qualquer entrypoint.
"""

# Consumidor do predictor_core via vendoring (telemetria JSONL etc.) — Shadow v2.

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass
