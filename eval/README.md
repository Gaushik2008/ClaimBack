# eval/

Benchmark and evaluation scripts. The protocol is in [`../docs/evaluation.md`](../docs/evaluation.md).

Planned contents:

- `build_benchmark.py`: parse awards into cases and split by date
- `run_baseline.py`: plain single-prompt LLM baseline
- `run_claimback.py`: full pipeline on the test set
- `metrics.py`: outcome agreement, clause match, citation check, calibration
- `results/`: saved run outputs (small summary files only)
