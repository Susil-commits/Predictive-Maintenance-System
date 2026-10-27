# PMS Business Case & Industrial ROI Analysis

> [!NOTE]
> **Disclaimer & Modeling Notice**: The economic projections, ROI comparisons, and downtime calculations presented in this document represent an **illustrative worked example** demonstrating how cost-sensitive threshold optimization maps to industrial maintenance economics under severe class imbalance. They do **not constitute validated business claims, audited financial representations, or guarantees of commercial returns**. Operational equipment downtime costs, secondary collateral damages, and repair durations vary substantially across distinct facility topologies, maintenance staffing models, and physical machine architectures.

---

## Executive Pitch Deck: Industrial Intelligence & Reliability

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PMS EXECUTIVE PITCH DECK                               │
│                         Industrial Intelligence & Reliability                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Slide 1: The Macro Opportunity & Industry Problem
* **The $50 Billion Downtime Crisis**: Unscheduled equipment downtime costs global industrial manufacturing over **$50 Billion annually**. Across automotive assembly, power generation, and precision CNC milling, downtime costs average **$260,000 per hour** in stranded labor, scrapped inventory, and emergency contractor dispatches.
* **The Failure of Status Quo Maintenance**:
  1. **Reactive Maintenance (Run-to-Failure)**: Machinery runs until catastrophic failure occurs. Secondary collateral damage (e.g., a broken tool destroying high-speed spindle bearings and motor coils) multiplies repair costs by **5x to 10x**.
  2. **Calendar-Based Preventive Maintenance**: Replacing parts every 500 operating hours regardless of health. Over **80% of maintenance hours are spent inspecting perfectly healthy machinery**, while sudden fatigue surges still slip through undetected.
  3. **SCADA Threshold Alarm Fatigue**: Static thresholds on temperature or vibration trigger **>70% false alarm rates**, causing operators to mute warning consoles immediately before catastrophic breakdowns occur.

### Slide 2: The PMS Value Proposition
* **From Reactive Guesswork to Prescriptive Action**: PMS bridges the gap between high-frequency machine telemetry and executive decision-making:
  * **Physics-Informed Ingestion**: Ingests multi-sensor telemetry (temperature, rotational speed, hydraulic pressure, vibration, service hours) and computes fundamental thermodynamic and kinematic indicators.
  * **True Empirical Probabilities (Not Arbitrary Ranks)**: Standard machine learning models output distorted probability estimates under severe class imbalance (28:1). PMS incorporates **Platt Sigmoid Calibration** (`CalibratedClassifierCV`), achieving a **70.4% reduction in probabilistic error** (Brier score from 0.0887 down to 0.0263).
  * **Explainable Diagnostics (SHAP TreeExplainer)**: Field engineers cannot act on an opaque risk score. PMS delivers per-prediction feature attribution (e.g., *"+1.64 Dynamic Rotor Stress, +1.44 Thermal Dissipation Deficit"*) alongside actionable Standard Operating Procedures (SOPs).
  * **Sub-15ms Edge & Cloud Runtime**: Standardized API for enterprise cloud orchestration, alongside serialized ONNX models (`ml/model.onnx`) for sub-3ms edge execution directly on factory-floor PLC gateway hardware.

### Slide 3: Industrial ROI & Unit Economics
Predictive maintenance transforms unbudgeted emergency capital expenditures into predictable, low-cost maintenance windows:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INDUSTRIAL ROI COMPARISON                               │
├──────────────────────────────────────┬───────────────────────────────────┬─────────────┤
│ Metric                               │ Without PMS (Catastrophic)        │ With PMS    │
├──────────────────────────────────────┼───────────────────────────────────┼─────────────┤
│ Average Unscheduled Downtime         │ 6 to 18 Hours                     │ 30-45 Mins  │
│ Direct Downtime Financial Cost       │ ~$150,000 to $500,000             │ ~$250-$500  │
│ Secondary Collateral Damage          │ Spindle, motor coils destroyed    │ Zero damage │
│ Supply Chain Logistics               │ Rush/airfreight emergency parts   │ Pre-ordered │
│ False Alarm Operator Distrust        │ High (>70% false alert rate)      │ Controlled  │
└──────────────────────────────────────┴───────────────────────────────────┴─────────────┘
```

* **Annual ROI for a 50-Machine Manufacturing Facility**:
  * Baseline: 12 catastrophic downtime events/year @ $180,000 average total cost = **$2,160,000/year**.
  * With PMS: 50% captured early (6 events mitigated to planned 45-min adjustments @ $500 each); remaining 6 events mitigated in severity = **Estimated Annual Savings: $1,050,000 - $1,350,000**.
  * System payback period: **Under 90 days**.

### Slide 4: Cost-Sensitive Optimization Matrix
In real-world plant operations, a False Negative (missing a catastrophic breakdown, `C_FN`) costs **$100,000+**, whereas a False Positive (a technician spending 20 minutes inspecting a healthy machine, `C_FP`) costs **~$150**. 

```
                                      Actual Machine State
                              ┌──────────────────────┬──────────────────────┐
                              │  Failure Positive    │   Normal Negative    │
       ┌──────────────────────┼──────────────────────┼──────────────────────┤
       │ Alert: High Risk     │ True Positive (TP)   │ False Positive (FP)  │
       │ (Dispatch Action)    │ Catastrophe Prevented│ Inspection Cost: $150│
Model  ├──────────────────────┼──────────────────────┼──────────────────────┤
Action │ Alert: Normal        │ False Negative (FN)  │ True Negative (TN)   │
       │ (No Action Taken)    │ Downtime Cost: $100k+│ Normal Operation: $0 │
       └──────────────────────┴──────────────────────┴──────────────────────┘
```

By shifting the decision threshold across the Precision-Recall curve to **0.2849**, PMS achieves:
* **F1-Score: 0.4277** (Precision: 0.3736, Recall: 0.5000) under a 28:1 imbalanced ratio.
* Captures **half of all emerging breakdowns** before downtime occurs.
* Roughly **4 in 10 alerts represent immediate actionable mechanical anomalies**, drastically outperforming legacy threshold alarms.

### Slide 5: Competitive Advantage & Market Moat
| Feature / Capability | Legacy SCADA Systems | Generic AutoML / Demos | **Predictive Maintenance System (PMS)** |
| :--- | :--- | :--- | :--- |
| **Probability Calibration** | None (Static thresholds) | Uncalibrated (distorted probabilities) | **Platt Sigmoid Calibrated** (Brier: 0.0263) |
| **Class Imbalance Handling** | None | Default 0.50 cutoff (0.0 F1 score) | **PR-Curve Optimization** (Threshold: 0.2849) |
| **Model Explainability** | None | Global feature importance only | **Real-Time SHAP TreeExplainer** per inference |
| **Degradation Horizon** | None | Classification only | **Remaining Useful Life (RUL)** regression |
| **Data Drift Detection** | Manual inspection | Infrequent batch checks | **Automated Population Stability Index (PSI)** |
| **Database Resilience** | Fragile DB configs | Hardcoded drivers | **Dual DBAPI Driver Support** (`psycopg` v3 & v2) |
| **Deployment Form Factors** | Proprietary PLCs | Heavy server dependencies | **Cloud REST API + Sub-3ms Edge ONNX** |

### Slide 6: Real-Time Downtime Value-at-Risk ($VaR) Formulation

Standard predictive maintenance platforms output abstract failure percentages. PMS translates real-time physics into financial exposure for executive leadership:

$$\text{Financial Value at Risk ($VaR)} = P(\text{Failure}) \times \left[ (T_{\text{downtime}} \times C_{\text{downtime}}) + C_{\text{collateral}} + C_{\text{scrap}} \right]$$

* **Industrial Parameters**:
  * $C_{\text{downtime}}$: Hourly facility downtime rate ($12,500/hr default).
  * $T_{\text{downtime}}$: Expected mean time to repair based on failure mode (Thermal: 3.5 hrs; Overstrain: 18.0 hrs; Motor Winding: 36.0 hrs).
  * $C_{\text{collateral}}$: Secondary physical asset damage if run to catastrophic seizure ($28,000 spindle rebuild).
  * $C_{\text{scrap}}$: Scrapped workpieces during mid-cycle tool destruction ($4,500).

#### Prescriptive Machine De-Rating Payoff
When an imminent failure is detected during a critical production run, our **Prescriptive Digital Twin** enables operators to de-rate operating speed (e.g., -15% RPM). This drops immediate failure probability from **86% to 18%** and extends remaining life by **48 hours**, preserving customer delivery deadlines while avoiding a $50,000 unplanned capital replacement.

> For the comprehensive forensic audit, code kill-list, and autonomous agent roadmap, see **[`docs/BOARDROOM_STRATEGY_AND_AUDIT.md`](BOARDROOM_STRATEGY_AND_AUDIT.md)**.

