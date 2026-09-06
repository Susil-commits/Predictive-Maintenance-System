# Standard Operating Procedure: Power Failure & Electrical Drive Overload (PWF)

## 1. Overview & Physical Mechanism
Power Failure (PWF) stems from electrical or electro-mechanical impedance mismatch in the motor drive system, where delivered mechanical power ($P = \tau \times \omega$) exceeds either the thermal rating of the motor stator windings or the current-limiting threshold of the Variable Frequency Drive (VFD). Power failures often manifest as sudden torque collapse, rotational stall, or thermal tripping under peak load.

## 2. Telemetry Symptoms & Risk Signatures
- **Primary Indicator**: Rotational speed (RPM) anomalies (abnormal high speed slip or sharp sub-baseline stall drop under load).
- **Secondary Correlation**: Elevated mechanical power index and RPM-vibration ratio.
- **Physical Clues**: VFD overcurrent fault codes (OC1/OC3), high motor surface temperature, electrical humming, and belt slippage smell.

## 3. Diagnostic & Inspection Protocol
1. **Three-Phase Current Balance**: Measure phase currents (L1, L2, L3) using a calibrated True-RMS clamp meter. Calculate phase unbalance percentage (unbalance > 3% indicates winding degradation or supply fault).
2. **Drive Inverter Diagnostics**: Interrogate VFD error logs via Modbus/fieldbus; check DC bus voltage ripple and IGBT heatsink thermistor records.
3. **Shaft Alignment & Coupling**: Check motor-to-gearbox angular and offset alignment using dual-laser alignment kit (tolerance < 0.05 mm).
4. **Insulation Resistance (Megger Test)**: Perform 1000V DC insulation resistance test between phase windings and motor frame ground (threshold > 100 MΩ).

## 4. Probable Root Causes
- Motor stator insulation degradation or inter-turn short circuit causing localized saturation.
- Excessive mechanical resistance in gearbox or spindle bearings resulting in high torque drag.
- Supply voltage transients, brownouts, or phase loss at main distribution panel.
- Incorrect VFD V/f (voltage/frequency) curve parameters or over-aggressive torque boost settings.

## 5. Prescriptive Remediation & Corrective Actions
- **Immediate (Safety)**: Restrict spindle load and cap maximum allowable speed to nominal baseline until motor diagnostic is complete.
- **Drive Tuning**: Re-tune VFD motor model parameters via auto-tuning sequence; verify current limiting ceiling and dynamic braking resistor function.
- **Mechanical Coupling Maintenance**: Replace worn elastomeric coupling inserts; realign motor and driven shaft within precision limits.
- **Electrical Verification**: Inspect and re-torque all power terminal connections to specified torque values (4.5 Nm on M6 terminals).
