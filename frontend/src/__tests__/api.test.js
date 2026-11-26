import test from 'node:test';
import assert from 'node:assert/strict';

import api, {
  API_BASE_URL,
  predictMaintenance,
  getHistory,
  getFleetSummary,
  getAssetRul,
  getWorkOrders,
  updateWorkOrderStatus,
  getInferenceBenchmark,
  verifyAuditChain,
  getFeedbackMetrics,
  exportFeedbackDataset,
} from '../api.js';

test('API_BASE_URL defaults to localhost:8000 without trailing slash', () => {
  assert.equal(API_BASE_URL, 'http://localhost:8000');
});

test('predictMaintenance passes runtime query parameter and payload', async () => {
  let captured = null;
  const origAdapter = api.defaults.adapter;
  api.defaults.adapter = async (config) => {
    captured = config;
    return {
      data: { failure_risk: 'LOW', probability: 0.02, runtime: 'onnx' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    };
  };

  try {
    const payload = { temperature: 80, rpm: 2000, pressure: 25, vibration: 0.3, operating_hours: 1000 };
    const res = await predictMaintenance(payload, 'onnx');
    assert.equal(res.runtime, 'onnx');
    assert.equal(captured.method, 'post');
    assert.equal(captured.url, '/predict?runtime=onnx');
    assert.deepEqual(JSON.parse(captured.data), payload);
  } finally {
    api.defaults.adapter = origAdapter;
  }
});

test('getHistory and getWorkOrders serialize optional filters cleanly', async () => {
  const urls = [];
  const origAdapter = api.defaults.adapter;
  api.defaults.adapter = async (config) => {
    urls.push({ method: config.method, url: config.url, data: config.data });
    return { data: [], status: 200, statusText: 'OK', headers: {}, config };
  };

  try {
    await getHistory(15, 'CNC-MILL-01');
    await getFleetSummary(200);
    await getAssetRul('CNC-MILL-01', 25);
    await getWorkOrders('CNC-MILL-01', 'RESOLVED', 30);
    await updateWorkOrderStatus('WO-2026-01', { status: 'RESOLVED', actual_failure_confirmed: true });
    await getInferenceBenchmark(50);
    await verifyAuditChain();
    await getFeedbackMetrics();
    await exportFeedbackDataset();

    assert.equal(urls[0].url, '/history?limit=15&asset_id=CNC-MILL-01');
    assert.equal(urls[1].url, '/fleet/summary?limit=200');
    assert.equal(urls[2].url, '/fleet/CNC-MILL-01/rul?window=25');
    assert.equal(urls[3].url, '/maintenance/work-orders?limit=30&asset_id=CNC-MILL-01&status=RESOLVED');
    assert.equal(urls[4].method, 'patch');
    assert.equal(urls[4].url, '/maintenance/work-orders/WO-2026-01');
    assert.equal(urls[5].url, '/inference/benchmark?iterations=50');
    assert.equal(urls[6].url, '/api/security/verify-chain');
    assert.equal(urls[7].url, '/mlops/feedback-metrics');
    assert.equal(urls[8].method, 'post');
    assert.equal(urls[8].url, '/mlops/export-feedback');
  } finally {
    api.defaults.adapter = origAdapter;
  }
});
