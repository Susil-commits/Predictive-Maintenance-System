import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import TelemetryForm from '../components/TelemetryForm';
import RULForecastCard from '../components/RULForecastCard';
import FleetOverviewPanel from '../components/FleetOverviewPanel';

const BASE_TELEMETRY = {
  temperature: 82.5,
  rpm: 1950,
  pressure: 26.0,
  vibration: 0.42,
  operating_hours: 1500,
};

describe('TelemetryForm', () => {
  it('renders telemetry controls, switches runtime, and submits payload', () => {
    const onChange = vi.fn();
    const onSubmit = vi.fn((e) => e.preventDefault());
    const onRuntimeChange = vi.fn();

    render(
      <TelemetryForm
        formData={BASE_TELEMETRY}
        onChange={onChange}
        onSubmit={onSubmit}
        loading={false}
        runtime="xgboost"
        onRuntimeChange={onRuntimeChange}
      />,
    );

    expect(screen.getByText('Telemetry Studio')).toBeInTheDocument();
    expect(screen.getByText('EVALUATE TELEMETRY')).toBeInTheDocument();

    fireEvent.click(screen.getByText('ONNX Edge (C++)'));
    expect(onRuntimeChange).toHaveBeenCalledWith('onnx');

    fireEvent.click(screen.getByRole('button', { name: /EVALUATE TELEMETRY/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('disables submission and shows progress state while loading', () => {
    render(
      <TelemetryForm
        formData={BASE_TELEMETRY}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        loading={true}
      />,
    );

    const submitBtn = screen.getByRole('button', { name: /EVALUATING SENSOR RISK/i });
    expect(submitBtn).toBeDisabled();
  });
});

describe('RULForecastCard', () => {
  it('renders empty state when no RUL forecast has been computed yet', () => {
    render(<RULForecastCard rulData={null} loading={false} />);
    expect(screen.getByText('RUL Degradation Forecast')).toBeInTheDocument();
    expect(screen.getByText(/Run telemetry inference to calculate equipment remaining useful life/i)).toBeInTheDocument();
  });

  it('renders cycles, hours, asset DB tag, and triggers recalculation', () => {
    const onRefresh = vi.fn();
    render(
      <RULForecastCard
        rulData={{ estimated_rul_cycles: 42, estimated_rul_hours: 21.0, confidence: 0.91 }}
        loading={false}
        onRefresh={onRefresh}
        rulSourceMeta={{ hasHistory: true, assetId: 'CNC-MILL-01', points: 18 }}
      />,
    );

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('(21.0 hours)')).toBeInTheDocument();
    expect(screen.getByText('[CNC-MILL-01 · DB History: 18 pts]')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Recalculate/i }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});

describe('FleetOverviewPanel', () => {
  it('renders empty message when no tracked assets exist', () => {
    render(<FleetOverviewPanel fleet={{ assets: [], total_assets: 0, critical_assets: 0 }} />);
    expect(screen.getByText(/No tracked assets yet/i)).toBeInTheDocument();
  });

  it('renders assets, toggles selection, and invokes simulation/refresh actions', () => {
    const onSelectAsset = vi.fn();
    const onRefresh = vi.fn();
    const onSimulateStream = vi.fn();

    render(
      <FleetOverviewPanel
        fleet={{
          total_assets: 2,
          critical_assets: 1,
          assets: [
            {
              asset_id: 'CNC-MILL-01',
              latest_failure_risk: 'HIGH',
              latest_probability: 0.87,
              prediction_count: 14,
            },
            {
              asset_id: 'LATHE-02',
              latest_failure_risk: 'LOW',
              latest_probability: 0.08,
              prediction_count: 9,
            },
          ],
        }}
        selectedAsset="CNC-MILL-01"
        onSelectAsset={onSelectAsset}
        onRefresh={onRefresh}
        onSimulateStream={onSimulateStream}
      />,
    );

    expect(screen.getByText('[2 assets · 1 critical]')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show All Assets' }));
    expect(onSelectAsset).toHaveBeenCalledWith(null);

    fireEvent.click(screen.getByRole('button', { name: /Simulate Live Fleet/i }));
    expect(onSimulateStream).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: /Sync Fleet/i }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
