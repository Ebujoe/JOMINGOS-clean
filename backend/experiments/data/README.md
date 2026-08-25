# experiments/data/physionet_2012_seta_cleaned.csv

## What this is

3,931 real ICU patients from the PhysioNet/Computing in Cardiology Challenge
2012 (set-a), one row per patient, built from the first 48 hours of each
patient's stay. Real in-hospital mortality is the outcome label. Openly
published, de-identified secondary data — no new ethics approval required to
use it.

**Cite both when using this dataset** (required by PhysioNet's data use policy):

- Goldberger, A. L., Amaral, L. A. N., Glass, L., Hausdorff, J. M., Ivanov, P. C., Mark, R. G., Mietus, J. E., Moody, G. B., Peng, C. K., & Stanley, H. E. (2000). PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. *Circulation, 101*(23), e215-e220. https://doi.org/10.1161/01.CIR.101.23.e215
- Silva, I., Moody, G., Scott, D. J., Celi, L. A., & Mark, R. G. (2012). Predicting in-hospital mortality of ICU patients: The PhysioNet/Computing in Cardiology Challenge 2012. *Computing in Cardiology, 39*, 245-248.

## Why this dataset, not the original Kaggle one

A 200,020-row Kaggle "human vital signs" dataset was tried first and rejected:
every single vital sign in it was confined to normal physiological ranges (e.g.
heart rate 60-99, all within the 51-110 NEWS2-normal band), and its "Risk
Category" label didn't track real clinical abnormality — mean vitals were
statistically indistinguishable between "High Risk" and "Low Risk" rows except
for a weak heart-rate difference. NEWS2 correctly scored ~0 for nearly every
row, which is the algorithm behaving correctly on unfit data, not a bug. That
dataset could not support a meaningful evaluation regardless of which
algorithm was tested against it.

## Columns

| Column | Meaning |
|---|---|
| `Patient ID` | PhysioNet RecordID |
| `Age`, `Gender` | Static admission fields |
| `Heart Rate` / `... (last)` | First and last recorded HR in the 48h window |
| `Respiratory Rate` / `... (last)` | First/last RR |
| `Temperature` / `... (last)` | First/last temp (°C) |
| `Systolic BP` / `... (last)` | First/last systolic BP (invasive SysABP preferred, non-invasive NISysABP as fallback) |
| `Diastolic BP` / `... (last)` | Same pattern for diastolic |
| `Oxygen Saturation` / `... (last)` | First/last SaO2 |
| `GCS` / `... (last)` | Glasgow Coma Scale |
| `Consciousness` | `'A'` if GCS == 15 (Alert), else `'Not Alert'` — a standard, documented simplification used as an ACVPU proxy, since PhysioNet doesn't record ACVPU directly |
| `In-hospital Death` | Real outcome, 0/1 |
| `Risk Category` | `'High Risk'` if died, else `'Low Risk'` — derived directly from the real outcome, not a synthetic rule |

## Known, honest limitations

- **Missingness is real, not hidden**: Respiratory Rate is missing for ~72% of
  patients, Oxygen Saturation for ~55%. This is genuine ICU documentation
  sparsity (intermittent measurement), not a processing error. NEWS2 scores
  are computed from whichever parameters are actually available per patient —
  matching real clinical practice with partial observations — but this means
  some patients' scores rest on fewer than six parameters.
- **The trend signal is a single first-vs-last 48h delta**, not the full
  rolling 4/8/12-reading window `vitals/utils/trend_engine.py` implements in
  production. This dataset only offers first/last snapshots per parameter, not
  a dense reading series, so a full rolling-window comparison isn't possible
  with this data as structured. State this as a simplification, not imply
  it's identical to the production trend engine.
- **In-hospital mortality is a real, strong outcome, but broader/later than
  "early deterioration."** A patient can deteriorate and recover, or
  deteriorate slowly beyond the 48h window captured here. Don't treat "predicts
  mortality" and "detects early deterioration" as interchangeable claims.
- 6 of the original 4,000 record files failed to parse (malformed rows) and
  were skipped — 3,931 of 4,000 patients made it into the final CSV.

## Results

**Primary result — elderly cohort (age >= 65), matching this research's actual target population**
(`python manage.py run_physionet_evaluation --min-age 65`; 2,146 patients, 859 in the test set,
17.1% real mortality). Use this version when citing results — the all-ages version below includes
patients as young as 15, which isn't the population this research is about.

| Metric | NEWS2 alone | NEWS2 + trend |
|---|---|---|
| Sensitivity | 23.1% | 55.1% |
| Specificity | 88.2% | 64.5% |
| PPV | 28.8% | 24.3% |
| F1 | 0.257 | 0.337 |
| ROC-AUC | 0.610 | 0.622 |

**All-ages result** (`python manage.py run_physionet_evaluation`, no age filter; 3,931 patients,
1,573 in the test set, 13.9% mortality) — kept as a secondary sensitivity check, not the headline
number, since almost half these patients are under 65:

| Metric | NEWS2 alone | NEWS2 + trend |
|---|---|---|
| Sensitivity | 26.0% | 58.0% |
| Specificity | 85.9% | 62.0% |
| PPV | 23.0% | 19.8% |
| F1 | 0.244 | 0.295 |
| ROC-AUC | 0.627 | 0.629 |

**Against this research plan's own targets** (Sensitivity >=85%, Specificity >=80%, F1 >=0.80,
ROC-AUC >=0.85, False Positive Rate <15%): only NEWS2 Compliance (all six parameters implemented)
and NEWS2-alone's specificity are met. Sensitivity, F1, ROC-AUC, and false-positive rate all fall
well short of the original targets on this dataset. State this directly rather than downplaying it
— see the full gap analysis for the honest interpretation (NEWS2 was designed and validated for
acute hospital deterioration, not ICU mortality prediction on a dataset this sparse; the targets in
the original plan may themselves need revising once real results exist to compare against, which is
a legitimate methodological finding in its own right).

**Read this carefully before citing it**: trend more than doubled sensitivity
at this fixed threshold, but specificity and PPV got worse — a real trade-off,
not a clean win. Sweeping every possible threshold and taking each approach's
own *best* F1 gives a fairer comparison: NEWS2 alone peaks at threshold 4 (not
the conventional 7) with F1 0.285; NEWS2+trend peaks at threshold 7 with F1
0.295 — only a ~3.5% relative improvement. Most of the dramatic-looking gain
in the fixed-threshold comparison is an artefact of NEWS2's conventional
clinical threshold not being well-calibrated for this specific population, not
strong independent evidence that trend information adds large amounts of
value. ROC-AUC barely moved (0.627 -> 0.629) even though sensitivity swung by
32 points at threshold 7 — since AUC measures discrimination across all
thresholds, a stable AUC alongside a big threshold-specific swing means the
combined score mostly redistributes where false positives/negatives fall,
rather than fundamentally improving separation between the two groups. Report
this nuance, not just the headline sensitivity number.

## Reproducing this file

Source: `https://physionet.org/files/challenge-2012/1.0.0/set-a/` (4,000
per-patient text files) + `Outcomes-a.txt` (real mortality labels), fetched
directly, no PhysioNet login required for this specific Challenge dataset
(unlike raw MIMIC-IV, which needs CITI training + credentialed access).
Parsing extracts the first and last numeric value per relevant parameter per
patient within the 48h window, joins on RecordID against the outcomes file,
and derives the Consciousness/Risk Category fields as described above.
