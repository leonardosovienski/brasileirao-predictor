import json
import sqlite3
from pathlib import Path
from urllib.request import urlopen
import pdfplumber

ROOT = Path(__file__).resolve().parent / "turn_split_2026"
ROOT.mkdir(exist_ok=True)
url = "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_BA_sica_Brasileiro_SA_rie_A_2026_d64996b4d8.pdf"
path = ROOT / "cbf_tabela_basica_2026.pdf"
if not path.exists():
    with urlopen(url, timeout=60) as response:
        content = response.read()
    assert content.startswith(b"%PDF-")
    path.write_bytes(content)
with pdfplumber.open(path) as pdf:
    print("PDF_PAGES", len(pdf.pages))
    texts = [page.extract_text() for page in pdf.pages]
    (ROOT / "cbf_tabela_basica_2026.txt").write_text("\n\n".join(texts), encoding="utf-8")
    print(texts[0])
    pdf.pages[0].to_image(resolution=100).save(ROOT / "source_page1.png")
    pdf.pages[5].to_image(resolution=100).save(ROOT / "source_page6.png")

repo = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
with sqlite3.connect((repo / "data/matches.db").as_uri() + "?mode=ro", uri=True) as conn:
    conn.execute("PRAGMA query_only=ON")
    print("SCHEMA", json.dumps(conn.execute("PRAGMA table_info(sofascore_matches)").fetchall()))
    rows = conn.execute("SELECT event_id,date,kickoff_at,home_team,away_team FROM sofascore_matches WHERE date>='2026-01-01' AND date<'2027-01-01' ORDER BY date,event_id").fetchall()
    metadata = [dict(zip(["event_id", "date", "kickoff_at", "home_team", "away_team"], row)) for row in rows]
    (ROOT / "local_2026_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("LOCAL_METADATA", json.dumps({"n":len(rows), "teams":sorted({row[3] for row in rows}|{row[4] for row in rows})}, ensure_ascii=False))
