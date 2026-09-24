"""Reserved adapter_paths of the Brasileirão domain (C24.1), empty in Stage A.

Stage B may add the envelope V2 adapter here (and only here). Nothing outside this package
imports it, and no entrypoint of Stage A reaches it (tests/conformance/test_import_closure.py).
The adapter must call the domain only through the adapter_api:
brasileirao_predictor.research_runtime.runner.Circuit.submit_request.
"""
