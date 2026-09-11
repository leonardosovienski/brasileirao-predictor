"""Create a bounded test-filter variant of the inspected disposable runtime lab."""
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
source = (repo/'tools/runtime_lab/run.py').read_text(encoding='utf-8')
source = source.replace('Path(__file__).resolve().parent', "Path('C:/BRASILEIRAO/brasileirao-predictor/tools/runtime_lab')")
source = source.replace('Path(__file__).with_name("kernel_synthetic.py")', "Path('C:/BRASILEIRAO/brasileirao-predictor/tools/runtime_lab/kernel_synthetic.py')")
source = source.replace('parser.add_argument("--diagnostics", action="store_true")', 'parser.add_argument("--diagnostics", action="store_true")\n    parser.add_argument("--test-filter", required=True)')
source = source.replace('if not args.cross_only:', 'if False:  # explicit .NET-only diagnosis, no unrelated Python suite')
source = source.replace('(["--filter", "FullyQualifiedName~KernelCrossProcessTests"] if args.cross_only else [])', '["--filter", args.test_filter]')
source = source.replace('(3 if args.cross_only else 4)', '3')
(root/'run_dotnet_cases.py').write_text(source,encoding='utf-8')
source = (Path('C:/BRASILEIRAO/work/reconciliation-2026-09-10')/'run_isolated.py').read_text(encoding='utf-8')
source = source.replace("(REPO / 'data/promotions_brasileirao_2018_2026.json').resolve(),",'')
source = source.replace("(REPO / 'reports/trial_draw_calibration_a10_2024.json').resolve(),",'')
(root/'run_isolated.py').write_text(source,encoding='utf-8')
