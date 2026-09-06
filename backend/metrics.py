"""
Prometheus Metrics Exporter for Predictive Maintenance System (PMS).
Tracks:
- Request latency histogram on /predict
- Prediction volume counters by risk level (HIGH vs LOW)
- Population Stability Index (PSI) drift gauges
"""

import threading
from typing import Dict, List, Optional

# Standard latency buckets for HTTP REST endpoints (in seconds)
LATENCY_BUCKETS: List[float] = [0.005, 0.010, 0.025, 0.050, 0.075, 0.100, 0.250, 0.500, 1.000, 2.500]

class MetricsRegistry:
    """Thread-safe Prometheus metrics registry."""
    def __init__(self):
        self._lock = threading.Lock()
        
        # Counters
        self.total_predictions = 0
        self.high_risk_predictions = 0
        self.low_risk_predictions = 0
        self.http_requests_total: Dict[str, int] = {}
        
        # Latency Histogram for /predict
        self.histogram_buckets = {b: 0 for b in LATENCY_BUCKETS}
        self.histogram_sum = 0.0
        self.histogram_count = 0
        
        # Gauges
        self.drift_detected = 0
        self.max_psi = 0.0
        self.feature_psi: Dict[str, float] = {}

    def record_predict_latency(self, duration_seconds: float) -> None:
        """Records a single /predict execution duration into the Prometheus histogram."""
        with self._lock:
            self.histogram_count += 1
            self.histogram_sum += duration_seconds
            for b in LATENCY_BUCKETS:
                if duration_seconds <= b:
                    self.histogram_buckets[b] += 1

    def record_prediction(self, risk: str) -> None:
        """Records prediction outcome (HIGH vs LOW)."""
        with self._lock:
            self.total_predictions += 1
            if risk.upper() == "HIGH":
                self.high_risk_predictions += 1
            else:
                self.low_risk_predictions += 1

    def record_http_request(self, method: str, path: str, status_code: int) -> None:
        """Records HTTP request count."""
        key = f"{method}_{path}_{status_code}"
        with self._lock:
            self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1

    def update_drift(self, drift_detected: bool, max_psi: float, feature_psis: Optional[Dict[str, float]] = None) -> None:
        """Updates drift gauges."""
        with self._lock:
            self.drift_detected = 1 if drift_detected else 0
            self.max_psi = float(max_psi)
            if feature_psis:
                self.feature_psi.update(feature_psis)

    def generate_prometheus_text(self) -> str:
        """Renders metrics in Prometheus text exposition format."""
        with self._lock:
            lines = [
                "# HELP pms_predictions_total Total number of equipment risk predictions evaluated",
                "# TYPE pms_predictions_total counter",
                f"pms_predictions_total {self.total_predictions}",
                f'pms_predictions_by_risk_total{{risk="HIGH"}} {self.high_risk_predictions}',
                f'pms_predictions_by_risk_total{{risk="LOW"}} {self.low_risk_predictions}',
                "",
                "# HELP pms_predictions_high_risk Total number of HIGH risk predictions",
                "# TYPE pms_predictions_high_risk counter",
                f"pms_predictions_high_risk {self.high_risk_predictions}",
                "",
                "# HELP pms_predictions_low_risk Total number of LOW risk predictions",
                "# TYPE pms_predictions_low_risk counter",
                f"pms_predictions_low_risk {self.low_risk_predictions}",
                "",
                "# HELP pms_predict_latency_seconds Latency histogram for equipment risk prediction /predict endpoint",
                "# TYPE pms_predict_latency_seconds histogram",
            ]
            
            # Histogram bucket lines
            for b in LATENCY_BUCKETS:
                count = self.histogram_buckets[b]
                lines.append(f'pms_predict_latency_seconds_bucket{{le="{b}"}} {count}')
            lines.append(f'pms_predict_latency_seconds_bucket{{le="+Inf"}} {self.histogram_count}')
            lines.append(f"pms_predict_latency_seconds_sum {self.histogram_sum:.6f}")
            lines.append(f"pms_predict_latency_seconds_count {self.histogram_count}")
            lines.append("")
            
            # Drift Gauges
            lines.extend([
                "# HELP pms_drift_detected Flag indicating whether data drift is detected (1=Drift, 0=Stable)",
                "# TYPE pms_drift_detected gauge",
                f"pms_drift_detected {self.drift_detected}",
                "",
                "# HELP pms_drift_max_psi Maximum Population Stability Index (PSI) observed across features",
                "# TYPE pms_drift_max_psi gauge",
                f"pms_drift_max_psi {self.max_psi:.4f}",
            ])
            
            # Feature PSI breakdowns if present
            if self.feature_psi:
                lines.append("")
                lines.append("# HELP pms_feature_psi Population Stability Index per feature")
                lines.append("# TYPE pms_feature_psi gauge")
                for feat, psi_val in sorted(self.feature_psi.items()):
                    lines.append(f'pms_feature_psi{{feature="{feat}"}} {psi_val:.4f}')
                    
            lines.append("")
            return "\n".join(lines)

# Singleton metrics instance
metrics = MetricsRegistry()
