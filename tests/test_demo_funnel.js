const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '..', 'static', 'assets', 'js', 'codejet-demo.js'), 'utf8');

function page({ sdk = true, captchaAvailable = true, captchaToken = 'TOKEN', watchTracking = false } = {}) {
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
  const qualifiedInput = { value: '' };
  const watch = { now: Date.now(), played: 0, requests: [] };
  const error = { hidden: true };
  const form = {
    submitted: false,
    getAttribute: () => 'test-site-key',
    addEventListener: (name, fn) => { formEvents[name] = fn; },
    querySelector: selector => ({ '[type="submit"]': submitButton,
      '[name="g-recaptcha-response"]': captchaInput, '[name="demo_qualified_token"]': qualifiedInput, '.demo-form-error': error })[selector],
    submit() { this.submitted = true; }
  };
  const player = {
    currentTime: 81,
    duration: 81,
    played: { length: 1, start() { return 0; }, end() { return watch.played; } },
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
    } : undefined,
    fetch: watchTracking ? async (url, options) => {
      watch.requests.push({url, options});
      return {ok:true, async json() {
        if (url.endsWith('/start')) return {watch_token:'start-token'};
        return {qualified_token:'qualified-token'};
      }};
    } : undefined,
    setTimeout: (fn) => { fn(); }
  };
  vm.runInNewContext(code, { window, document, Array, Date: {now:() => watch.now} });
  return { window, document, player, playerEvents, endCard, replayEvents, replay,
    contact, ctaEvents, playCover, playEvents, playError, videoShell, formEvents, form, submitButton, captchaInput, qualifiedInput, watch, error };
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


test('opening the demo does not initiate a watch or a Google lead', () => {
  const p = page({watchTracking:true});
  assert.equal(p.watch.requests.length, 0);
  assert.equal(p.qualifiedInput.value, '');
});

test('play click alone and seeking to the end do not qualify a lead', async () => {
  const p = page({watchTracking:true});
  p.playEvents.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.watch.requests.filter(r => r.url.endsWith('/start')).length, 1);
  p.watch.now += 60_000;
  p.player.currentTime = 80;
  p.watch.played = 2;
  p.playerEvents.timeupdate();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.watch.requests.filter(r => r.url.endsWith('/qualify')).length, 0);
  assert.equal(p.qualifiedInput.value, '');
});

test('clicked demo with at least half actually played can attach a qualification token', async () => {
  const p = page({watchTracking:true});
  p.playEvents.click();
  await new Promise(resolve => setImmediate(resolve));
  p.watch.now += 43_000;
  p.watch.played = 41;
  p.playerEvents.timeupdate();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.watch.requests.filter(r => r.url.endsWith('/qualify')).length, 1);
  const payload = JSON.parse(p.watch.requests.at(-1).options.body);
  assert.equal(payload.duration_seconds, 81);
  assert.equal(payload.played_seconds, 41);
  assert.equal(p.qualifiedInput.value, 'qualified-token');
  p.formEvents.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.form.submitted, true);
});

test('a form can still be submitted when video tracking is unavailable', async () => {
  const p = page({watchTracking:false});
  p.formEvents.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.qualifiedInput.value, '');
  assert.equal(p.form.submitted, true);
});
