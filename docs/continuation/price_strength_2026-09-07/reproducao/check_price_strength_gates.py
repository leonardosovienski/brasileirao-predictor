"""Run only read-only scientific containment checks in the isolated checkout."""
from brasileirao_scripts import ci_check

ci_check.check_research_readonly()
ci_check.check_current_elo_containment()
if ci_check.failures:
    raise RuntimeError(ci_check.failures)
print('Read-only research and current-Elo containment gates passed.')
