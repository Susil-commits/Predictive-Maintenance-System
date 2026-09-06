import os
import io
import zipfile
import urllib.request
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
RAW_CSV = os.path.join(DATA_DIR, "ai4i2020.csv")
PROCESSED_CSV = os.path.join(DATA_DIR, "equipment_maintenance_data.csv")
UCI_URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"

def download_and_prepare_dataset():
    """
    Downloads UCI AI4I 2020 Predictive Maintenance Dataset and maps it
    to standard vehicle/equipment telemetry:
    - temperature (°C)
    - rpm
    - pressure (bar)
    - vibration (g)
    - operating_hours (hrs)
    - failure (0 = Healthy, 1 = Failure Risk)
    """
    print("Fetching UCI AI4I 2020 Predictive Maintenance Dataset...")
    df_raw = None
    
    if os.path.exists(RAW_CSV):
        print(f"Using local cached dataset: {RAW_CSV}")
        df_raw = pd.read_csv(RAW_CSV)
    else:
        try:
            req = urllib.request.Request(UCI_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                zip_bytes = resp.read()
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for filename in z.namelist():
                        if filename.endswith(".csv"):
                            with z.open(filename) as f:
                                df_raw = pd.read_csv(f)
                                df_raw.to_csv(RAW_CSV, index=False)
                                print(f"Saved raw dataset to {RAW_CSV}")
                                break
        except Exception as e:
            print(f"Warning: Could not download from UCI ({e}). Synthesizing based on AI4I distribution...")
            
    if df_raw is None or len(df_raw) == 0:
        # High fidelity synthesis conforming to AI4I 2020 distribution
        np.random.seed(42)
        n = 10000
        air_temp = np.random.normal(300, 2, n)
        proc_temp = air_temp + np.random.normal(10, 1, n)
        rpm = np.random.normal(1538, 179, n)
        torque = np.random.normal(40, 10, n)
        tool_wear = np.random.uniform(0, 250, n)
        
        # Physics-based failure criteria
        pwf = (torque * rpm * (2 * np.pi / 60) < 3500) | (torque * rpm * (2 * np.pi / 60) > 9000)
        hdf = (proc_temp - air_temp < 8.6) & (rpm < 1380)
        osf = (tool_wear * torque > 11000)
        failure = (pwf | hdf | osf | (np.random.rand(n) < 0.01)).astype(int)
        
        df_raw = pd.DataFrame({
            "Air temperature [K]": air_temp,
            "Process temperature [K]": proc_temp,
            "Rotational speed [rpm]": rpm,
            "Torque [Nm]": torque,
            "Tool wear [min]": tool_wear,
            "Machine failure": failure
        })
        df_raw.to_csv(RAW_CSV, index=False)
        print(f"Created dataset at {RAW_CSV}")

    # Standardize column names if needed
    col_map = {
        'Air temperature [K]': 'air_temp',
        'Process temperature [K]': 'process_temp',
        'Rotational speed [rpm]': 'rotational_speed',
        'Torque [Nm]': 'torque',
        'Tool wear [min]': 'tool_wear',
        'Machine failure': 'failure'
    }
    df = df_raw.rename(columns=col_map)
    
    np.random.seed(42)
    n = len(df)

    # Convert to typed float64 numpy arrays to ensure type safety and avoid pandas Series/Categorical conflicts
    air_temp_arr = np.asarray(df['air_temp'], dtype=np.float64)
    proc_temp_arr = np.asarray(df['process_temp'], dtype=np.float64)
    rpm_raw_arr = np.asarray(df['rotational_speed'], dtype=np.float64)
    torque_raw_arr = np.asarray(df['torque'], dtype=np.float64)
    wear_raw_arr = np.asarray(df['tool_wear'], dtype=np.float64)
    failure_arr = np.asarray(df['failure'], dtype=np.int32)

    # Feature mapping to equipment telemetry (independent noise, no label leakage):
    # 1. Temperature (°C): Add independent noise, not failure-conditional
    proc_min, proc_max = proc_temp_arr.min(), proc_temp_arr.max()
    proc_temp_norm = (proc_temp_arr - proc_min) / (proc_max - proc_min + 1e-5)
    temp_base = 68.0 + proc_temp_norm * 14.0
    temp_degradation = (wear_raw_arr / 250.0) * 3.5
    # Random thermal fluctuation uncorrelated with failure
    temp_random_spike = np.random.normal(0, 1.5, n)  # ← independent noise only
    temperature = np.clip(temp_base + temp_degradation + temp_random_spike, 55.0, 115.0)

    # 2. RPM: 1000 - 3200 RPM
    rpm = np.clip(rpm_raw_arr, 1000.0, 3200.0).round()

    # 3. Pressure: Add independent noise, not surge-conditional
    torq_min, torq_max = torque_raw_arr.min(), torque_raw_arr.max()
    torque_norm = (torque_raw_arr - torq_min) / (torq_max - torq_min + 1e-5)
    pressure_base = 20.0 + torque_norm * 14.0
    pressure_random_variation = np.random.normal(0, 1.0, n)  # ← independent, not failure-driven
    pressure = np.clip(pressure_base + pressure_random_variation, 16.0, 48.0)

    # 4. Vibration: Add independent noise, not wear/overstrain-conditional
    wear_min, wear_max = wear_raw_arr.min(), wear_raw_arr.max()
    wear_norm = (wear_raw_arr - wear_min) / (wear_max - wear_min + 1e-5)
    vib_base = 0.20 + wear_norm * 0.15  # Only wear directly, not failure flags
    vib_random_noise = np.random.normal(0, 0.04, n)  # ← independent noise
    vibration = np.clip(vib_base + vib_random_noise, 0.12, 1.25)

    # 5. Operating Hours: 200 - 6000 hrs (derived from tool wear accumulation)
    operating_hours = np.clip(200.0 + wear_norm * 4800.0 + np.random.normal(0, 50, n), 100.0, 6500.0).round()
    
    # Extract failure mode flags for segmented performance analysis
    hdf = df_raw['HDF'].fillna(0).astype(int) if 'HDF' in df_raw.columns else pd.Series(0, index=df.index)
    osf = df_raw['OSF'].fillna(0).astype(int) if 'OSF' in df_raw.columns else pd.Series(0, index=df.index)
    twf = df_raw['TWF'].fillna(0).astype(int) if 'TWF' in df_raw.columns else pd.Series(0, index=df.index)
    pwf = df_raw['PWF'].fillna(0).astype(int) if 'PWF' in df_raw.columns else pd.Series(0, index=df.index)
    rnf = df_raw['RNF'].fillna(0).astype(int) if 'RNF' in df_raw.columns else pd.Series(0, index=df.index)

    def determine_failure_type(row):
        if row['failure'] == 0:
            return 'Normal'
        types = []
        if row['hdf'] == 1:
            types.append('Thermal Failure')
        if row['osf'] == 1:
            types.append('Overstrain Failure')
        if row['twf'] == 1:
            types.append('Tool Wear Failure')
        if row['pwf'] == 1:
            types.append('Power Failure')
        if row['rnf'] == 1:
            types.append('Random Failure')
        return types[0] if types else 'Other Failure'

    clean_df = pd.DataFrame({
        "temperature": temperature.round(1),
        "rpm": rpm.astype(int),
        "pressure": pressure.round(1),
        "vibration": vibration.round(2),
        "operating_hours": operating_hours.astype(int),
        "failure": df['failure'].astype(int),
        "hdf": hdf,
        "osf": osf,
        "twf": twf,
        "pwf": pwf,
        "rnf": rnf
    })
    clean_df['failure_type'] = clean_df.apply(determine_failure_type, axis=1)
    
    clean_df.to_csv(PROCESSED_CSV, index=False)
    print(f"Processed dataset saved to {PROCESSED_CSV} (Total rows: {len(clean_df)}, Failure rate: {clean_df['failure'].mean():.2%})")
    print("Failure Mode Breakdown in dataset:")
    print(clean_df['failure_type'].value_counts())
    return clean_df

if __name__ == "__main__":
    download_and_prepare_dataset()
