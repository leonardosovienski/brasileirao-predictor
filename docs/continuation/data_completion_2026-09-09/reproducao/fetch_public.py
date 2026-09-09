"""Single public GET per registered URL; preserve response bytes and provenance."""

import hashlib
import json
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URLS = {
    "oddspapi_quota": "https://oddspapi.io/us/docs/requests-and-quota",
    "oddspapi_account": "https://oddspapi.io/us/docs/get-account",
    "oddspapi_history": "https://oddspapi.io/us/docs/get-historical-odds",
    "oddspapi_bookmakers": "https://oddspapi.io/us/docs/get-bookmakers",
    "oddspapi_current_odds": "https://oddspapi.io/us/docs/get-odds",
    "football_data_brazil": "https://www.football-data.co.uk/brazil.php",
    "football_data_notes": "https://www.football-data.co.uk/notes.txt",
    "football_data_bra_csv": "https://www.football-data.co.uk/new/BRA.csv",
    "football_data_bra_origin_csv": "https://football-data.co.uk/new/BRA.csv",
    "the_odds_api_history": "https://the-odds-api.com/historical-odds-data/",
    "odds_api_io_free": "https://odds-api.io/pricing/free",
    "betfair_spec": "https://historicdata.betfair.com/files/Betfair-Historical-Data-Feed-Specification.pdf",
    "betfair_historic_access": "https://betfair-datascientists.github.io/data/usingHistoricDataSite/",
    "bet365_br_terms": "https://help.bet365.bet.br/s/pt-br/terms-and-conditions",
    "bet365_br_soccer": "https://help.bet365.bet.br/s/pt-br/sportsrules/soccer",
    "rfb_tax_2025": "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/formularios/impostos/pagamento-aposta-de-quota-fixa-e-fantasy-sport/aplicativo.html",
    "spa_authorized_operators": "https://www.gov.br/fazenda/pt-br/composicao/orgaos/secretaria-de-premios-e-apostas/lista-de-empresas/empresas-autorizadas-1/empresas-autorizadas",
}


def main():
    out = ROOT / "public_sources"
    out.mkdir(exist_ok=False)
    rows = []
    for name, url in URLS.items():
        row = {"source": name, "url": url, "requested_at": datetime.now(UTC).isoformat(), "authenticated": False}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "brasileirao-research-data-audit/1"})
            with urllib.request.urlopen(request, timeout=25, context=ssl.create_default_context()) as response:
                raw = response.read(15_000_001)
                row.update(
                    http_status=response.status,
                    received_at=datetime.now(UTC).isoformat(),
                    final_url=response.url,
                    content_type=response.headers.get("Content-Type"),
                    date_header=response.headers.get("Date"),
                )
            if len(raw) > 15_000_000:
                raise ValueError("response_too_large")
            name_ext = name + (".pdf" if ".pdf" in url else ".csv" if ".csv" in url else ".html")
            (out / name_ext).write_bytes(raw)
            row.update(status="SAVED", file=name_ext, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        except urllib.error.HTTPError as exc:
            row.update(status="HTTP_FAILURE", http_status=exc.code)
        except Exception as exc:
            row.update(status="FETCH_FAILURE", error_type=type(exc).__name__)
        row["finished_at"] = datetime.now(UTC).isoformat()
        rows.append(row)
        (out / "manifest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"source": name, "status": row["status"], "http_status": row.get("http_status")}), flush=True)


if __name__ == "__main__":
    main()
