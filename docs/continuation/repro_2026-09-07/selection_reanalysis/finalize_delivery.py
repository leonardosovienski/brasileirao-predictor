"""Finalize documentation and verify existing artifacts; never fit or acquire data."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT = ROOT.parents[1] / "outputs" / "REANALISE"

packager = ROOT / "package_price_results.py"
source = packager.read_text(encoding="utf-8")
replacements = {
    "com13jogos": "com 13 jogos", "em3,35% nos9jogos": "em 3,35% nos 9 jogos",
    "encontrou177eventos": "encontrou 177 eventos", "de2026": "de 2026",
    "feitas30chamadas": "feitas 30 chamadas", "histórico:22HTTP200 e8HTTP429": "histórico: 22 respostas HTTP 200 e 8 respostas HTTP 429",
    "de61para62": "de 61 para 62", "Raw privado": "O histórico bruto privado",
    "teve22vetores": "teve 22 vetores", "teve7 emT−1h": "teve 7 em T−1h",
    "de6horas": "de 6 horas", "ficou4treino/3teste": "ficou com 4 eventos de treino e 3 de teste",
    "dePinnacle": " de Pinnacle", "mesmos30IDs, split20/10": "mesmos 30 IDs, divisão de 20 para treino e 10 para teste",
    "ealpha": "e o parâmetro de regularização", "ridge1e−4": "ridge de 1e−4",
    "a feature de outra casa": "a variável da outra casa",
    "Restaram13eventos de treino e9de teste": "Restaram 13 eventos de treino e 9 de teste",
    "emT−10min": "em T−10min", "desdeT−6h": "desde T−6h",
    "os22vetores": "os 22 vetores", "entreT−1h eT−10min": "entre T−1h e T−10min",
    "foi−0,3199": "foi −0,3199", "em5dos9eventos": "em 5 dos 9 eventos",
    "de{rmse0:.4f}para{rmse1:.4f}pontos": "de {rmse0:.4f} para {rmse1:.4f} pontos",
    "diagnósticoC": "diagnóstico C", "de2%": "de 2%",
    "referênciaPinnacle": "referência Pinnacle", "parserEXP001": "leitor de históricos EXP001",
    "parteB permanece em namespace": "pesquisa B permanece em uma pasta separada",
    "tem97testespytest": "tem 97 testes pytest", "de11verificações": "de 11 verificações",
    "as13.680decisões": "as 13.680 decisões",
    "Nenhuma CI completa foi alegada.": "Essas verificações cobrem os componentes alterados e os experimentos; a suíte completa do projeto não foi executada.",
    "[históricoOddsPapi]": "[histórico OddsPapi]",
}
for old, new in replacements.items():
    source = source.replace(old, new)
source = source.replace("apenas  de Pinnacle", "apenas de Pinnacle").replace("margem  de Pinnacle", "margem de Pinnacle")
packager.write_text(source, encoding="utf-8")

checkpoint = """## CHECKPOINT — REANÁLISE HISTÓRICA E CORREÇÃO EXP001 (2026-09-07)

O operador pediu nova análise e execução de alternativas para seleção/confiança.
Foram geradas 1.697 previsões de 1.900 jogos de 2021–2025 já observados; 12
políticas previamente fixadas foram avaliadas em 1.140 eventos de 2023–2025.
Com custo adicional simulado de 2% por unidade, confiança ≥60% teve 239 apostas
virtuais e ROI −7,34%; ≥70% teve somente 20 e ROI +4,82%, revertido no estresse.
Nenhuma política demonstrou vantagem robusta. Odds agregadas e disponibilidade
histórica de placares/xG limitam a interpretação; não são execução real.

Correção operacional aplicada em brasileirao_scripts/exp001_data_pilot.py:
selecionar o último estado antes de verificar atividade; rejeitar suspensão,
atividade não confirmada e conflitos simultâneos. Evita ressuscitar uma odd
antiga. A cobertura nominal anterior de 245/245 não comprova disponibilidade;
seu impacto histórico não pode ser quantificado sem as timelines originais.

Pesquisa B/C independente, no primeiro semestre de 2026 já observado e anterior
às coortes protegidas: 30 históricos selecionados antes dos preços, 22 respostas
válidas e 8 HTTP 429, sem repetição/substituição. Quota gratuita 61→62 devido ao
catálogo; gasto zero. Plano original exigindo as duas casas: 4 treino/3 teste,
INSUFFICIENT_DATA, nenhum ajuste executado. C não teve candidato no teste.

Após conhecer a cobertura, uma segunda decisão explicitamente adaptativa foi
registrada antes dos ajustes: mesmos IDs e critérios, somente Pinnacle. Com
13 eventos de treino e 9 de teste, ridge de movimento reduziu MSE em 3,35% contra
persistência, mas retirar um evento pode inverter a vantagem. WATCH: sinal
pequeno e frágil para eventual replicação, sem prova de EV, execução ou lucro.
Esta análise não substitui o resultado insuficiente do protocolo original.
As duas decisões estão em docs/decisions/2026-09-07-price-discovery-*.md.

Verificação: 97 testes aprovados; 11 verificações sintéticas independentes dos
analisadores de preço; reconciliação independente de 13.680 decisões. Os 14
hashes de arquivos protegidos permanecem iguais. Não foram abertos resultados
das coortes H14/H15/H9/A1, nem alterados seus protocolos, registro de trials,
agendamentos ou habilitação de capital. Não houve apostas, compra ou nova conta.

Experimentos desta reanálise encerrados conforme os planos; não continuar
ajustando parâmetros ou ampliando a amostra para forçar um resultado positivo.
Entregas: Documents/Codex/2026-09-07/le/outputs/REANALISE/RESULTADOS.md e
PRICE_DISCOVERY.md, dados derivados, planos, testes e pacotes de reprodução.
Os históricos brutos do provedor permanecem privados na pasta work da sessão.
Este checkpoint acrescenta o diagnóstico atual e preserva os anteriores.
"""
handoff = REPO / "HANDOFF.md"
body = handoff.read_text(encoding="utf-8-sig")
assert checkpoint.splitlines()[0] not in body, "Checkpoint already applied; do not duplicate"
first, rest = body.split("\n", 1)
quoted = "\n".join("> " + line if line else ">" for line in checkpoint.splitlines())
handoff.write_text(first + "\n\n" + quoted + "\n" + rest, encoding="utf-8")
(OUT / "CHECKPOINT_FINAL.md").write_text(checkpoint, encoding="utf-8")

integrity_path = OUT / "integridade.json"
integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
expected = integrity["protected_sha256"]
assert len(expected) == 14
mismatches = [name for name, value in expected.items()
              if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != value]
assert not mismatches, mismatches
integrity["checked_at"] = datetime.now(timezone.utc).isoformat()
integrity["protected_files_unchanged"] = True
integrity["verification_scope"] = "97 component and experiment tests; not the full project suite"
integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for path in OUT.glob("*.zip"):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, path
        assert not any("/raw/" in name.replace("\\", "/") for name in archive.namelist()), path
print(json.dumps({"protected_hashes_verified": len(expected), "checkpoint": str(OUT / "CHECKPOINT_FINAL.md"), "zip_checks": "passed"}))
