"""Adapter mínimo do Brasileirão para o registry do ecosystem-predictor.

Este módulo expõe somente metadados e saúde do adaptador. Não promove resultado
científico, não gera aposta e não autoriza capital.
"""

from __future__ import annotations


class BrasileiraoPredictorPlugin:
    name = "brasileirao-predictor"
    domain = "brasileirao"

    def health(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "status": "WAITING",
            "version": "0.1.0",
            "details": {
                "mode": "shadow",
                "adapter": "plugin-v1",
                "note": "saúde do domínio deve ser derivada dos jobs; adapter não promove readiness",
            },
        }

    def capabilities(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "supports_prediction": True,
            "supports_settlement": False,
            "supports_collection": True,
            "scientific_status": "UNKNOWN",
            "predictive_status": "UNKNOWN",
            "economic_status": "NOT_VALIDATED",
            "capital_permission": "FORBIDDEN",
            "extra": {
                "mode": "shadow",
                "manual_execution": True,
                "source_of_scientific_truth": "HANDOFF.md",
            },
        }


PLUGIN = BrasileiraoPredictorPlugin()
