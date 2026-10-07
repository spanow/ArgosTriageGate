# Argos, Triage Gate

Route an application incident to the team that must act, before calling expensive agents.

The gate uses a 2B-parameter **decision model**: no text generation, a probability distribution over options
defined per request, plus a NONE gate to say "nothing fits". Two models are compared, both built on
Qwen3.5-2B-Base: **Wazn-2B v0.1** ([numidlabs/wazn-2b-v0.1](https://huggingface.co/numidlabs/wazn-2b-v0.1)) and
**Strands Decider 2B v21** ([StrandsAgents](https://huggingface.co/StrandsAgents)), against a regex baseline.

## Results

NVIDIA L4 GPU. Full report: [`results/eval_report.md`](results/eval_report.md).

| | Wazn-2B | Strands Decider 2B | Rules |
|---|---|---|---|
| Main set (65 incidents), accuracy | 58% | **83%** | 94% ¹ |
| Wrong automatic actions (threshold 0.6) | 11 | 6 | 3 |
| Non-Java set (24 Python, Node, Go, Nginx logs), accuracy | 67% | **96%** | 29% |
| Right owning team out of 36 | **5/5** | n/a ² | n/a |
| Median inference latency | 153 ms | 246 ms | < 1 ms |

1. Rules and main-set incidents share an author; the non-Java set is the fairer test.
2. Strands accepts at most 24 options per question.

## Run

Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run triage data/samples/payment_timeout.log --adapter rules
uv run python -m triage.eval.report        # rebuilds results/eval_report.md from results/
```

Models on a GPU with [Modal](https://modal.com):

```bash
uv run modal setup
uv run modal run cloud/modal_app.py --model wazn      # main, non-Java, large-K, preprocessing ablation
uv run modal run cloud/modal_app.py --model strands   # main, non-Java
```

## Layout

| Path | |
|---|---|
| `triage/preprocessing` | exception chain down to the root cause, application frames, normalisation |
| `triage/domain`, `triage/adapters` | `DecisionPort` and its adapters: Wazn, Strands, rules |
| `triage/policy` | NONE gate, then threshold, then route; escalation with the top-k leads |
| `triage/eval` | runner, metrics, report |
| `data/` | taxonomy, labelled incidents, 36-team catalogue |
| `cloud/modal_app.py` | model server and evaluation in one GPU container |
| `victim-app/` | Spring Boot 4 app that produces the real errors behind the incidents (NPE, exhausted pool, timeouts, TLS, OOM) |

