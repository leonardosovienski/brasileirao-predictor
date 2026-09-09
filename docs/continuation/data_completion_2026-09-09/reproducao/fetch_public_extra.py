"""Additional official source documentation; no authenticated endpoints."""

import importlib.util
from pathlib import Path

path = Path(__file__).with_name("fetch_public.py")
spec = importlib.util.spec_from_file_location("public_source_capture", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = path.parent / "extra_docs"
module.ROOT.mkdir(exist_ok=False)
module.URLS = {
    "football_data_brazil_origin": "https://football-data.co.uk/brazil.php",
    "football_data_notes_origin": "https://football-data.co.uk/notes.txt",
    "football_data_source_warning": "https://football-data.co.uk/data",
    "oddspapi_free_plan": "https://oddspapi.io/us/sign-up",
    "betfair_spec_australia": "https://historicdata.betfair.com.au/Betfair-Historical-Data-Feed-Specification.pdf",
}
module.main()
