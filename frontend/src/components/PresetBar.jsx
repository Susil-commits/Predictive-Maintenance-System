import React from 'react';
import { BookmarkCheck, AlertTriangle, CheckCircle, Flame, Gauge } from 'lucide-react';

export default function PresetBar({ onSelectPreset }) {
  const presets = [
    {
      label: 'Target Sample (High Risk)',
      icon: AlertTriangle,
      highlight: true,
      data: {
        temperature: 92.4,
        rpm: 2800,
        pressure: 31.5,
        vibration: 0.64,
        operating_hours: 4820
      }
    },
    {
      label: 'Healthy Baseline',
      icon: CheckCircle,
      highlight: false,
      data: {
        temperature: 68.0,
        rpm: 1500,
        pressure: 21.0,
        vibration: 0.22,
        operating_hours: 950
      }
    },
    {
      label: 'Thermal Overheat',
      icon: Flame,
      highlight: false,
      data: {
        temperature: 97.2,
        rpm: 2300,
        pressure: 27.8,
        vibration: 0.42,
        operating_hours: 3100
      }
    },
    {
      label: 'Vibration & Fatigue',
      icon: Gauge,
      highlight: false,
      data: {
        temperature: 79.5,
        rpm: 3100,
        pressure: 33.0,
        vibration: 0.72,
        operating_hours: 5300
      }
    }
  ];

  return (
    <div className="presets-container">
      <span className="presets-label">
        <BookmarkCheck size={14} />
        Presets:
      </span>
      {presets.map((p, idx) => {
        const Icon = p.icon;
        return (
          <button
            key={idx}
            type="button"
            className={`preset-btn ${p.highlight ? 'highlight' : ''}`}
            onClick={() => onSelectPreset(p.data)}
          >
            <Icon size={14} />
            {p.label}
          </button>
        );
      })}
    </div>
  );
}
