"""O registro real de tentativas conforma ao schema do core.

`predictor_core.contracts.registry.validate_trials` diz, na própria docstring:
"A suíte do consumidor deve falhar se o trials.json real não conformar — o
registro só protege o DSR se todo campo do denominador for interpretável."
Esta é essa suíte. Sem ela, `data/trials.json` podia derivar do schema em
silêncio e o Deflated Sharpe pararia de descontar as tentativas corretamente —
que é o mecanismo anti-p-hacking inteiro do projeto.
"""

from __future__ import annotations

import json
from pathlib import Path

from predictor_core.contracts.registry import TrialRegistry, validate_trials

ROOT = Path(__file__).resolve().parent.parent
TRIALS = ROOT / "data" / "trials.json"


def test_trials_json_existe_e_e_uma_lista() -> None:
    assert TRIALS.exists(), f"{TRIALS} ausente — é o denominador do DSR, não é opcional"
    assert isinstance(json.loads(TRIALS.read_text(encoding="utf-8")), list)


def test_trials_json_conforma_ao_schema_do_core() -> None:
    erros = validate_trials(TrialRegistry(TRIALS).load())
    assert erros == [], "violações de schema em data/trials.json:\n  " + "\n  ".join(erros)


def test_nomes_de_trial_sao_unicos() -> None:
    """Nome é a IDENTIDADE da configuração no registro. Duplicata faria duas
    hipóteses diferentes contarem como uma no denominador."""
    nomes = [t["name"] for t in TrialRegistry(TRIALS).load()]
    assert len(nomes) == len(set(nomes)), f"nomes duplicados: {sorted({n for n in nomes if nomes.count(n) > 1})}"


def test_toda_trial_declara_status() -> None:
    """`status` é o que separa hipótese aberta de veredito. Trial sem status
    não é interpretável na leitura do registro."""
    sem_status = [t["name"] for t in TrialRegistry(TRIALS).load() if not t.get("status")]
    assert sem_status == [], f"trials sem status: {sem_status}"


# O core valida `status` apenas como string não-vazia (`validate_trial_v2`), então
# variantes ortográficas do mesmo veredito — "substituida" vs "substituída" —
# passavam pelo schema e quebravam qualquer leitura agregada do registro (contagem
# por status, filtro de hipóteses ainda abertas). O vocabulário é fechado por
# decisão de governança; é o consumidor que precisa travá-lo.
STATUS_VOCABULARY = frozenset(
    {
        "pre-registrada",
        "exploratoria",
        "informativa",
        "inconclusiva",
        "refutada",
        "comprovada",
        "substituida",
    }
)

TRIALS_V2 = ROOT / "data" / "trials.v2.json"


def test_status_pertence_ao_vocabulario_fechado() -> None:
    for caminho in (TRIALS, TRIALS_V2):
        registro = json.loads(caminho.read_text(encoding="utf-8"))
        fora = sorted({t["status"] for t in registro if t.get("status") not in STATUS_VOCABULARY})
        assert fora == [], f"{caminho.name}: status fora do vocabulário: {fora}"


def test_status_por_trial_e_o_mesmo_nas_duas_geracoes_do_registro() -> None:
    """v1 e v2 descrevem as MESMAS tentativas. Divergência de veredito entre elas
    significa que uma das duas mentiu sobre o estado de uma hipótese."""
    v1 = {t["name"]: t["status"] for t in json.loads(TRIALS.read_text(encoding="utf-8"))}
    v2 = {t["trial_id"]: t["status"] for t in json.loads(TRIALS_V2.read_text(encoding="utf-8"))}
    assert set(v1) == set(v2), f"identidades divergentes: {sorted(set(v1) ^ set(v2))}"
    divergentes = {k: (v1[k], v2[k]) for k in v1 if v1[k] != v2[k]}
    assert divergentes == {}, f"status divergente entre v1 e v2: {divergentes}"
