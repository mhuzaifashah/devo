# Devo Test Runbook

Use this file as the quick command reference for validating the Devo agent test suite.

## 1) Install and sync deps

```powershell
uv sync
```

## 2) Fast gate on every change (no real LLM call)

```powershell
uv run pytest -q -m "not integration"
```

Expected: compaction/hooks/features tests run only.

## 3) Run only compaction + hooks/features tests

```powershell
uv run pytest tests/test_compaction.py tests/test_hooks_and_features.py -q
```

## 4) Run frontend LLM session test (real provider/model)

Set env vars in PowerShell:

```powershell
$env:AIAGENT_RUN_LLM_TESTS="1"
$env:AIAGENT_TEST_PROVIDER="<provider>"
$env:AIAGENT_TEST_MODEL="<model>"
$env:AIAGENT_TEST_FRONTEND_DIR="D:\Code\Python\AGENT CODING\frontend"
```

Run:

```powershell
uv run pytest tests/test_frontend_llm_session.py -q
```

## 5) Run full suite including integration

```powershell
$env:AIAGENT_RUN_LLM_TESTS="1"
$env:AIAGENT_TEST_PROVIDER="<provider>"
$env:AIAGENT_TEST_MODEL="<model>"
uv run pytest -q
```

## 6) Optional verbose output for debugging

```powershell
uv run pytest -vv -s
```

## Notes

- `tests/test_frontend_llm_session.py` is integration-style and uses real model/tool calls.
- If `AIAGENT_RUN_LLM_TESTS` is not `1`, integration test is intentionally skipped.
- Default frontend target is `D:\Code\Python\AGENT CODING\frontend`, override with `AIAGENT_TEST_FRONTEND_DIR`.
- CI workflows:
  - `.github/workflows/unit-tests.yml` runs fast gate tests on every push/PR.
  - `.github/workflows/integration-tests.yml` runs integration tests:
    - on prompt/tool-related changes
    - nightly schedule
    - pre-release (`release: prereleased`)
