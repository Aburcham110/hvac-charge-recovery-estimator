# HVAC/R Charge / Recovery Estimator (Educational)

Python **stdlib-only** CLI that approximates **additional refrigerant charge** for field line-sets and compares to a current charge (add vs recover).

> **Educational only — not an OEM charge procedure.**  
> Use manufacturer charts, weighed-in charge, and a refrigerant-rated digital manifold for real work.

## Method (approximate)

1. Start from **factory/nameplate charge** (lb).
2. Subtract a **factory-included liquid line length** (preset by system type, overridable).
3. Apply educational **oz/ft liquid-line factors** by refrigerant + copper OD.
4. Optionally add a small **suction-line** contribution, plus receiver/extra lb.
5. If `--current-lbs` is given, report estimated **add** or **recover**.

Documented assumptions print on every report.

## Supported refrigerants

`R-410A` · `R-22` · `R-134a` · `R-404A` · `R-407C` · `R-32` · `R-454B`

## Quick start

```bash
cd hvac-charge-recovery-estimator
python3 charge_estimator.py --help
python3 charge_estimator.py -i
```

### Split AC example (50 ft liquid beyond 25 ft included)

```bash
python3 charge_estimator.py \
  --system split-ac \
  --refrigerant R-410A \
  --factory-lbs 6.0 \
  --liquid-ft 50 --liquid-od 3/8 \
  --suction-ft 50 --suction-od 5/8 \
  --current-lbs 6.5
```

### Walk-in with full field liquid line

```bash
python3 charge_estimator.py \
  --system walk-in \
  --refrigerant R-404A \
  --factory-lbs 12 \
  --liquid-ft 40 --liquid-od 1/2 \
  --suction-ft 40 --suction-od 5/8 \
  --receiver-lbs 2 \
  --current-lbs 18
```
