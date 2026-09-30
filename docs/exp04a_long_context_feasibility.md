# Exp 4A — Long-context feasibility

Notebook: `notebooks/exp04a_long_context_feasibility.ipynb`. Output: `results/current/development/exp04a_feasibility.csv`, plot `results/current/plots/exp04a_corpus_size.png`. Cost about $0.02.

**Question:** does the full policy corpus fit each model's context, at what cost, and is it feasible?

| Variant | gpt-4o-mini | gemini-2.5-flash-lite | llama3.2:3b (local) |
|---|---|---|---|
| Full corpus (22 docs, commentary included) | 49,095 tokens, $0.0075/claim | 51,870 tokens, $0.0053/claim | needs a 65k window; 244 s/claim (4.7 h for 70 claims) |
| Lean (normative clauses only) | 16,592 tokens, $0.0026/claim | 18,893 tokens, $0.0020/claim | 16.8k tokens at a 24k window; 34 s/claim (0.7 h for 70) |

**Findings:** everything fits the paid models' context (128k, ~1M). 76% of the full corpus is interpretive commentary. Ollama's default 16,384 window silently truncates both corpora to about 8.2k tokens, so the local setup must raise the window. A characters/4 estimate (68k) overstated the real token count.

**Decision:** 4B runs full on gpt-4o-mini and gemini, lean on all three; dev split only; projected $1.21.
