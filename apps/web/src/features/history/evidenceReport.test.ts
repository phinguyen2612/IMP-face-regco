import {expect, it} from 'vitest';
import type {FacePresenceEvent} from '../../api/simpleRecognition';
import {evidenceReportCsv} from './evidenceReport';

it('exports stranger events with Vietnamese evidence states and escapes CSV formulas and quotes', () => {
  const event = {id: 'a', kind: 'UNKNOWN_ALERT', camera_name: '=Camera,"cổng"', recognized_at: '2026-11-04T08:00:00Z', consecutive_unknown: 5, evidence_status: 'EXPIRED'} as FacePresenceEvent;
  const csv = evidenceReportCsv([event, {...event, id: 'entry', kind: 'FACE_CAPTURED'}]);
  expect(csv.startsWith('\uFEFF')).toBe(true);
  expect(csv).toContain('"\'=Camera,""cổng"""');
  expect(csv).toContain('Ảnh đã hết hạn');
  expect(csv).not.toContain('"entry"');
  expect(csv).toContain('15:00:00');
});
