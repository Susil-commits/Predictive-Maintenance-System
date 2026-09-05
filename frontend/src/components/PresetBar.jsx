import React from 'react';
import { BookmarkCheck, AlertTriangle, ShieldCheck, Flame, Activity } from 'lucide-react';

export default function PresetBar({ onSelectPreset }) {
  const presets = [
    {
      tag: '01',
      label: 'Target Sample [High-Risk]',
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
      tag: '02',
      label: 'Nominal Baseline',
      icon: ShieldCheck,
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
      tag: '03',
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
      tag: '04',
      label: 'Vibration & Fatigue',
      icon: Activity,
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
        <BookmarkCheck size={13} />
        Presets
      </span>
      {presets.map((p, idx) => {
        const Icon = p.icon;
        return (
          <button
            key={idx}
            type="button"
            className={`preset-btn ${p.highlight ? 'highlight' : ''}`}
            onClick={() => onSelectPreset(p.data)}
            title={`Load ${p.label}`}
          >
            <span style={{ color: 'var(--text-dim)', fontSize: '0.66rem' }}>{p.tag}</span>
            <Icon size={12} />
            <span>{p.label}</span>
          </button>
        );
      })}
    </div>
  );
}

