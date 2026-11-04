import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it} from 'vitest';
import type {FacePresenceEvent} from '../../api/simpleRecognition';
import {EvidenceMedia} from './EvidenceMedia';

afterEach(cleanup);
it('keeps a readable fallback when a ready image cannot be loaded', () => {
  render(<EvidenceMedia event={{id:'e',kind:'UNKNOWN_ALERT',evidence_status:'READY',evidence_key:'face-test.jpg'} as FacePresenceEvent}/>);
  fireEvent.error(screen.getByRole('img'));
  expect(screen.getByText('Không tải được ảnh minh chứng.')).toBeTruthy();
  expect(screen.queryByRole('img')).toBeNull();
});
