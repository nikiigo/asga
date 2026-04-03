# Example Runs

This document collects concrete simulation examples produced with the shipped configs.

## 1000-Step Full-Strategy Run

This example uses:

- `config_1000_steps_all_strategies_20_fast.json`
- `config_1000_steps_all_strategies_20_render_static.json`

Workflow:

```bash
.venv/bin/python main.py --config config_1000_steps_all_strategies_20_fast.json
.venv/bin/python main.py --render-config config_1000_steps_all_strategies_20_render_static.json --render-from-metrics sample_output_1000_all_strategies_20_fast/metrics.json
```

Summary from the generated run:

- steps: `1000`
- final population: `541`
- final unique strategies: `110`
- winning strategy: `FIRST_BY_TIDEMAN_AND_CHIERUZZI`
- winning group size: `94`
- final cooperation rate: `0.900`
- final dominant share: `0.174`

Saved example artifacts:

- HTML report: [report_1000_steps_all_strategies_20.html](examples/report_1000_steps_all_strategies_20.html)
- Infographic: ![1000-step full-strategy example](examples/report_1000_steps_all_strategies_20.png)
