import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ZAKADI_SUBPROTOCOL, ERROR_CODES, isErrorCode, TERMINAL_STATES, terminalStateForEnd, CloseCode, SESSION_STATES } from '../dist/index.js';

test('subprotocol is zakadi.v1', () => {
  assert.equal(ZAKADI_SUBPROTOCOL, 'zakadi.v1');
});

test('there are 18 error codes and isErrorCode narrows correctly', () => {
  assert.equal(ERROR_CODES.length, 18);
  assert.ok(isErrorCode('interrupted'));
  assert.equal(isErrorCode('not_a_code'), false);
});

test('redial is offered only for recoverable terminal states', () => {
  assert.equal(TERMINAL_STATES.incomplete.offersRedial, true);
  assert.equal(TERMINAL_STATES.completed.offersRedial, false);
  assert.equal(TERMINAL_STATES.unsupported_device.offersRedial, false);
});

test('end reasons map to terminal states', () => {
  assert.equal(terminalStateForEnd('ok'), 'completed');
  assert.equal(terminalStateForEnd('attempts_exhausted'), 'incomplete');
  assert.equal(terminalStateForEnd('admission'), 'error');
});

test('close codes and states are complete', () => {
  assert.equal(CloseCode.CancelledByUser, 4010);
  assert.equal(SESSION_STATES.length, 7);
});
