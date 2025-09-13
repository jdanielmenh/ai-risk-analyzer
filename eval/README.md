# Evaluation dataset

Synthetic, company-specific financial questions targeting interest-rate sensitivity and debt servicing. Each question includes parameters (ticker, period, bps) and gold scoring config (targets + tolerances). Gold numeric values must be computed at eval-time from FMP + filings; this avoids stale ground truth and reflects real-time pipelines.

File: questions.jsonl

- id: unique id
- ticker: company symbol
- period: latest (quarter) for now
- bps: interest rate shock in basis points
- question: natural language prompt
- gold:
  - targets: which outputs to score (delta_interest, coverage_pre/post, coverage_delta, debt_service_pct_post)
  - formula_notes: documentation for calculator
  - tolerances: absolute tolerances (delta_interest_abs in USD) and/or pct_abs for ratios
- gold_sources:
  - expected_nodes: likely SEC sections
  - expected_endpoints: expected FMP endpoints aliases (as in FreeRiskAPI)

Notes

- At eval-time, a calculator derives numeric gold from fetched metrics. If some fields are missing, tasks are skipped or marked unsupported.
