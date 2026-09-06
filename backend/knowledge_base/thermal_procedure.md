# Standard Operating Procedure: Thermal Dissipation & Heat Dissipation Failure (HDF)

## 1. Overview & Physical Mechanism
Heat Dissipation Failure occurs when the thermal energy generated during continuous mechanical operation (bearing friction, fluid shear, and electrical rotor losses) exceeds the dissipation capacity of the cooling and lubrication circuit. Operating temperatures above 80°C accelerate lubricant oxidation, reduce kinematic viscosity below hydrodynamic film thresholds, and induce differential thermal expansion across machine tolerances.

## 2. Telemetry Symptoms & Risk Signatures
- **Primary Indicator**: Operating temperature exceeding baseline threshold (T > 80.0°C; critical alarm T > 92.0°C).
- **Secondary Correlation**: Elevated temperature-pressure index and thermal excess metrics.
- **Physical Clues**: Discolored heat exchanger surfaces, burnt oil odor, localized hotspot thermograms, and cooling loop pressure drops.

## 3. Diagnostic & Inspection Protocol
1. **Thermal Imaging Survey**: Perform infrared thermography on bearing housings, motor casing, and heat exchanger cores to localize hotspots (>10°C delta across symmetry).
2. **Coolant Flow & Quality Verification**: Check coolant circulating pump differential pressure and flow meter readings. Inspect fluid color, clarity, and particulate contamination.
3. **Heat Exchanger Integrity**: Check radiator fins and plate channels for external dust clogging, lime scale deposition, or internal fouling.
4. **Sensor & Transducer Check**: Verify calibration of RTD / thermocouple temperature probes against a calibrated infrared pyrometer.

## 4. Probable Root Causes
- External blockage of air louvers or convective cooling radiators.
- Cavitation, impeller wear, or partial air-lock in the coolant circulation pump.
- Thermal paste degradation between sensor housing and stator block.
- Viscosity loss or thermal breakdown of hydraulic/lubricant oil resulting in boundary friction.

## 5. Prescriptive Remediation & Corrective Actions
- **Immediate (Safety)**: Reduce mechanical spindle RPM and cycle load by 20–30% until temperature drops below 75°C.
- **Mechanical Service**: Backflush heat exchanger plates with descaling solvent; blow down radiator cooling fins with compressed nitrogen.
- **Fluid Maintenance**: Drain degraded coolant/lubricant, flush circuit, and refill with ISO VG 46/68 synthetic oil meeting high-temp specifications.
- **Transducer Recalibration**: Recalibrate RTD thermistors and confirm dual-channel redundant temperature verification.
