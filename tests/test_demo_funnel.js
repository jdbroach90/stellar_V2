const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '..', 'static', 'assets', 'js', 'codejet-demo.js'), 'utf8');

function page({ sdk = true, captchaAvailable = true, captchaToken = 'TOKEN' } = {}) {
  const playerEvents = {};
  const endCard = { hidden: true };
  const replayEvents = {};
  const playEvents = {};
  const playCover = { hidden: false, dataset: {}, addEventListener: (name, fn) => { playEvents[name] = fn; } };
  const playError = { hidden: true };
  const lock = new Set(['demo-play-locked']);
  const videoShell = { classList: { contains: name => lock.has(name), remove: name => lock.delete(name) } }; 
  const replay = { addEventListener: (name, fn) => { replayEvents[name] = fn; } };
  const contact = { classList: { classes: [], add(x) { this.classes.push(x); } } };
  const ctaEvents = {};
  const cta = { addEventListener: (name, fn) => { ctaEvents[name] = fn; } };
  const formEvents = {};
  const submitButton = { disabled: false };
  const captchaInput = { value: '' };
  const error = { hidden: true };
  const form = {
    submitted: false,
    getAttribute: () => 'test-site-key',
    addEventListener: (name, fn) => { formEvents[name] = fn; },
    querySelector: selector => ({ '[type="submit"]': submitButton,
      '[name="g-recaptcha-response"]': captchaInput, '.demo-form-error': error })[selector],
    submit() { this.submitted = true; }
  };
  const player = {
    currentTime: 81,
    muted: true,
    playCalls: 0,
    addEventListener: (name, fn) => { playerEvents[name] = fn; },
    play() { this.playCalls++; return Promise.resolve(); }
  };
  const elements = { 'stream-player': {}, 'demo-video-ended': endCard, 'demo-replay': replay, 'demo-contact': contact, 'demo-play': playCover, 'demo-play-error': playError, 'demo-video-shell': videoShell };
  const document = {
    getElementById: id => elements[id],
    querySelector: selector => selector === '[data-cj-demo-form]' ? form : null,
    querySelectorAll: selector => selector === 'a[href="#demo-contact"]' ? [cta] : []
  };
  const window = {
    Stream: sdk ? () => player : undefined,
    grecaptcha: captchaAvailable ? {
      ready(fn) { fn(); }, execute() { return Promise.resolve(captchaToken); }
    } : undefined
  };
  vm.runInNewContext(code, { window, document, Array });
  return { window, document, player, playerEvents, endCard, replayEvents, replay,
    contact, ctaEvents, playCover, playEvents, playError, videoShell, formEvents, form, submitButton, captchaInput, error };
}

test('the existing analytics player is exposed and the completion CTA appears', () => {
  const p = page();
  assert.equal(p.window.codejetDemoPlayer, p.player);
  assert.equal(p.endCard.hidden, true);
  p.playerEvents.ended();
  assert.equal(p.endCard.hidden, false);
  p.ctaEvents.click();
  assert.ok(p.contact.classList.classes.includes('demo-contact-highlight'));
});

test('replay resets video to the start and hides the completion CTA', async () => {
  const p = page();
  p.playerEvents.ended();
  p.replayEvents.click();
  assert.equal(p.player.currentTime, 0);
  assert.equal(p.endCard.hidden, true);
});


test('video does not play until the user clicks the large Play with sound button', async () => {
  const p = page();
  assert.equal(p.player.playCalls, 0);
  assert.equal(p.playCover.hidden, false);
  assert.equal(p.videoShell.classList.contains('demo-play-locked'), true);
  assert.equal(p.playCover.dataset.playerReady, 'true');
  p.playEvents.click();
  assert.equal(p.player.currentTime, 0);
  assert.equal(p.player.muted, false);
  assert.equal(p.player.playCalls, 1);
  assert.equal(p.playCover.hidden, true);
  assert.equal(p.videoShell.classList.contains('demo-play-locked'), false);
});

test('replay uses sound and does not count as automatic playback', () => {
  const p = page();
  p.playerEvents.ended();
  p.replayEvents.click();
  assert.equal(p.player.muted, false);
  assert.equal(p.player.playCalls, 1);
});

test('missing player SDK reveals native iframe controls on click', () => {
  const p = page({ sdk: false });
  assert.equal(p.playCover.hidden, false);
  assert.equal(p.playError.hidden, true);
  p.playEvents.click();
  assert.equal(p.playCover.hidden, true);
  assert.equal(p.videoShell.classList.contains('demo-play-locked'), false);
  assert.equal(p.playError.hidden, false);
});

test('SDK failure leaves the form functional', async () => {
  const p = page({sdk: false});
  assert.equal(p.window.codejetDemoPlayer, undefined);
  p.formEvents.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.form.submitted, true);
});

test('form submits only after a nonempty captcha token arrives', async () => {
  const p = page();
  let prevented = false;
  p.formEvents.submit({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(p.submitButton.disabled, true);
  assert.equal(p.form.submitted, false);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.captchaInput.value, 'TOKEN');
  assert.equal(p.form.submitted, true);
  assert.equal(p.error.hidden, true);
});

test('missing captcha does not send and exposes fallback message', () => {
  const p = page({captchaAvailable: false});
  p.formEvents.submit({preventDefault() {}});
  assert.equal(p.form.submitted, false);
  assert.equal(p.submitButton.disabled, false);
  assert.equal(p.error.hidden, false);
});

test('empty captcha token does not send', async () => {
  const p = page({captchaToken: ''});
  p.formEvents.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.form.submitted, false);
  assert.equal(p.submitButton.disabled, false);
  assert.equal(p.error.hidden, false);
});
