/* Run with: node --test tests/test_analytics_client.js */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

const repo = path.resolve(__dirname, '..');
const tracker = fs.readFileSync(path.join(repo, 'static/assets/js/codejet-analytics.js'), 'utf8');
const demo = fs.readFileSync(path.join(repo, 'templates/demo.html'), 'utf8');
const demoInline = demo.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const storageKey = 'codejet_demo_visit_v1';

function timeRanges(pairs) {
    return {length: pairs.length, start: i => pairs[i][0], end: i => pairs[i][1]};
}

function response(status, data) {
    return {status, ok: status >= 200 && status < 300, json: async () => data};
}

function harness(options = {}) {
    let now = 1800000000000;
    let nextTimer = 0;
    const timers = new Map();
    const listeners = {};
    const windowListeners = {};
    const docListeners = {};
    const calls = [];
    const stored = new Map();
    if (options.stored) stored.set(storageKey, JSON.stringify(options.stored));
    const player = {
        currentTime: 0,
        duration: 100,
        paused: true,
        played: timeRanges([]),
        addEventListener(name, fn) { (listeners[name] ||= []).push(fn); },
        emit(name) { for (const fn of listeners[name] || []) fn(); }
    };
    Object.assign(player, options.playerState || {});
    const page = options.page || '/demo';
    const tag = {getAttribute(name) {
        return {'data-cj-page': page, 'data-cj-video-id': page === '/demo' ? '38ccab99e8156adae4abcfbb1d36cc0f' : ''}[name];
    }};
    const document = {
        referrer: options.referrer || '',
        visibilityState: 'visible',
        querySelector: () => tag,
        getElementById: () => ({}),
        addEventListener(name, fn) { (docListeners[name] ||= []).push(fn); },
        emit(name) { for (const fn of docListeners[name] || []) fn(); }
    };
    function goodVisit() {
        return response(200, {visit_token: 'signed-visit-token', visit_id: 'f25702cd-1355-41a3-b120-84086b8b88c8', expires_at: now / 1000 + 14400});
    }
    const window = {
        crypto: webcrypto,
        location: {search: options.search || '', href: 'https://codejet.app' + page},
        sessionStorage: {
            getItem(key) { if (options.blockStorage) throw new Error('Storage blocked'); return stored.get(key) || null; },
            setItem(key, value) { if (options.blockStorage) throw new Error('Storage blocked'); stored.set(key, value); },
            removeItem(key) { stored.delete(key); }
        },
        setTimeout(fn, delay) { const id = ++nextTimer; timers.set(id, {fn, due: now + delay}); return id; },
        clearTimeout(id) { timers.delete(id); },
        addEventListener(name, fn) { (windowListeners[name] ||= []).push(fn); },
        emit(name) { for (const fn of windowListeners[name] || []) fn(); },
        fetch(url, init) {
            const call = {url, init, body: JSON.parse(init.body)};
            calls.push(call);
            if (options.fetch) return options.fetch(call, goodVisit);
            return Promise.resolve(url.endsWith('/visit') ? goodVisit() : response(204));
        }
    };
    class ClockDate extends Date { static now() { return now; } }
    const context = vm.createContext({
        window, document,
        navigator: options.navigator || {},
        Date: ClockDate, URL, URLSearchParams, Uint8Array, AbortController,
        setTimeout: window.setTimeout,
        Stream: () => player
    });
    if (page === '/demo') vm.runInContext(demoInline, context);
    vm.runInContext(tracker, context);
    async function settle() { for (let i = 0; i < 40; i++) await Promise.resolve(); }
    async function advance(ms) {
        now += ms;
        for (const [id, timer] of [...timers]) {
            if (timer.due <= now) { timers.delete(id); timer.fn(); }
        }
        await settle();
    }
    function events() {
        const unique = new Map();
        for (const c of calls.filter(c => c.url.endsWith('/event'))) unique.set(c.body.event_id, c.body);
        return [...unique.values()];
    }
    return {calls, player, window, document, stored, settle, advance, events, goodVisit};
}

test('homepage sends only allowlisted campaign metadata and a referrer hostname', async () => {
    const h = harness({page: '/', search: '?utm_source=mailer&utm_campaign=november&email=private%40example.com', referrer: 'https://ref.example/path?email=private%40example.com'});
    await h.settle();
    assert.equal(h.calls.length, 1);
    const body = h.calls[0].body;
    assert.equal(body.page, '/');
    assert.deepEqual(body.campaign, {utm_source: 'mailer', utm_campaign: 'november'});
    assert.equal(body.referrer_host, 'ref.example');
    assert.equal(JSON.stringify(body).includes('private'), false);
    assert.deepEqual(Object.keys(body).sort(), ['campaign', 'event_id', 'page', 'referrer_host']);
});

test('playing after buffering or seeking produces one start per player load', async () => {
    const h = harness();
    await h.settle();
    h.player.emit('playing');
    h.player.emit('playing');
    h.player.emit('seeked');
    h.player.emit('playing');
    await h.settle();
    assert.equal(h.events().filter(e => e.event_type === 'video_started').length, 1);
    assert.equal(h.events().length, 1);
});

test('seeking to the end records actual played ranges, not 100 percent watched', async () => {
    const h = harness();
    await h.settle();
    h.player.played = timeRanges([[0, 5]]);
    h.player.currentTime = 5;
    h.player.emit('playing');
    h.player.emit('seeking');
    h.player.currentTime = 100;
    h.player.emit('timeupdate');
    h.player.emit('seeked');
    h.player.emit('ended');
    await h.settle();
    const ended = h.events().find(e => e.event_type === 'video_ended');
    assert.equal(ended.position_seconds, 100);
    assert.equal(ended.duration_seconds, 100);
    assert.equal(ended.played_seconds, 5);
    assert.equal(h.calls.filter(c => c.url.endsWith('/event')).every(c => c.init.keepalive), true);
});

test('unsupported played ranges and nonfinite metrics remain unknown', async () => {
    const h = harness();
    await h.settle();
    h.player.played = undefined;
    h.player.duration = Infinity;
    h.player.currentTime = NaN;
    h.player.emit('playing');
    await h.settle();
    const start = h.events()[0];
    assert.equal(start.played_seconds, null);
    assert.equal(start.position_seconds, null);
    assert.equal(start.duration_seconds, null);
});

test('start and end wait for slow visit initialization, without delaying the existing redirect', async () => {
    let releaseVisit;
    const h = harness({fetch(call) {
        if (call.url.endsWith('/visit')) return new Promise(resolve => { releaseVisit = resolve; });
        return Promise.resolve(response(204));
    }});
    await h.settle();
    h.player.emit('playing');
    h.player.played = timeRanges([[0, 100]]);
    h.player.currentTime = 100;
    h.player.emit('ended');
    await h.settle();
    assert.equal(h.events().length, 0);
    await h.advance(1000);
    assert.equal(h.window.location.href, 'https://codejet.app/#contact');
    releaseVisit(h.goodVisit());
    await h.settle();
    assert.deepEqual(h.events().map(e => e.event_type), ['video_started', 'video_ended']);
});

test('blocked sessionStorage does not disable the current page visit or video', async () => {
    const h = harness({blockStorage: true});
    await h.settle();
    h.player.emit('playing');
    h.player.emit('ended');
    await h.settle();
    assert.equal(h.events().length, 2);
    await h.advance(1000);
    assert.equal(h.window.location.href, 'https://codejet.app/#contact');
});

test('GPC and DNT suppress telemetry and preserve the video end redirect', async () => {
    for (const navigator of [{globalPrivacyControl: true}, {doNotTrack: '1'}]) {
        const h = harness({navigator});
        await h.settle();
        h.player.emit('playing');
        h.player.emit('ended');
        await h.advance(1000);
        assert.equal(h.calls.length, 0);
        assert.equal(h.window.location.href, 'https://codejet.app/#contact');
    }
});

test('disabled or rejected analytics cannot break playback or cause retries', async () => {
    const h = harness({fetch: async () => response(403)});
    await h.settle();
    h.player.emit('playing');
    h.player.emit('ended');
    await h.advance(1000);
    assert.equal(h.calls.length, 1);
    assert.equal(h.window.location.href, 'https://codejet.app/#contact');
});

test('a backend privacy opt-out response is accepted without a JSON body or retry', async () => {
    const h = harness({fetch: async () => response(204)});
    await h.settle();
    h.player.emit('playing');
    await h.advance(1000);
    assert.equal(h.calls.length, 1);
});

test('a failed event is retried with the same event ID', async () => {
    let failed = false;
    const h = harness({fetch(call, goodVisit) {
        if (call.url.endsWith('/visit')) return Promise.resolve(goodVisit());
        if (!failed) { failed = true; return Promise.reject(new TypeError('Network unavailable')); }
        return Promise.resolve(response(204));
    }});
    await h.settle();
    h.player.emit('playing');
    await h.settle();
    await h.advance(1000);
    const attempts = h.calls.filter(c => c.url.endsWith('/event'));
    assert.equal(attempts.length, 2);
    assert.equal(attempts[0].body.event_id, attempts[1].body.event_id);
});

test('rejected cached visit token clears inherited attribution and retries idempotently', async () => {
    const h = harness({
        stored: {visit_token: 'old-token', expires_at: 1800009999, campaign: {utm_source: 'mailer'}},
        fetch(call, goodVisit) {
            if (call.body.visit_token === 'old-token') return Promise.resolve(response(401));
            return Promise.resolve(goodVisit());
        }
    });
    await h.settle();
    assert.equal(h.calls.length, 2);
    assert.equal(h.calls[0].body.event_id, h.calls[1].body.event_id);
    assert.equal(h.calls[1].body.visit_token, undefined);
    assert.deepEqual(h.calls[1].body.campaign, {});
    assert.equal(JSON.parse(h.stored.get(storageKey)).visit_token, 'signed-visit-token');
});

test('expired or malformed cached visits cannot attribute a later direct visit to a mailer', async () => {
    for (const stored of [
        {visit_token: 'expired-token', expires_at: 1799999999},
        {visit_token: '', expires_at: 1800009999},
        {visit_token: null, expires_at: 1800009999},
        {visit_token: 'bad-expiry-token', expires_at: 'invalid'},
        {visit_token: 'x'.repeat(513), expires_at: 1800009999}
    ]) {
        const h = harness({stored: {...stored, campaign: {utm_source: 'mailer', utm_campaign: 'old'}}});
        await h.settle();
        assert.equal(h.calls[0].body.visit_token, undefined);
        assert.deepEqual(h.calls[0].body.campaign, {});
        assert.deepEqual(JSON.parse(h.stored.get(storageKey)).campaign, {});
    }
});

test('a live cached visit preserves campaign across homepage and demo navigation', async () => {
    const h = harness({stored: {visit_token: 'live-token', expires_at: 1800009999, campaign: {utm_source: 'mailer'}}});
    await h.settle();
    assert.equal(h.calls[0].body.visit_token, 'live-token');
    assert.deepEqual(h.calls[0].body.campaign, {utm_source: 'mailer'});
});

test('expiry while the page is open also clears inherited campaign on renewal', async () => {
    const h = harness({stored: {visit_token: 'live-token', expires_at: 1800009999, campaign: {utm_source: 'mailer'}}});
    await h.settle();
    h.player.emit('playing');
    await h.settle();
    await h.advance(14401000);
    h.player.currentTime = 30;
    h.player.played = timeRanges([[0, 30]]);
    h.player.emit('timeupdate');
    await h.settle();
    const visits = h.calls.filter(c => c.url.endsWith('/visit'));
    assert.equal(visits.length, 2);
    assert.deepEqual(visits[1].body.campaign, {});
    assert.equal(visits[1].body.visit_token, undefined);
});

test('attaching after playback began records one start after visit initialization', async () => {
    const h = harness({
        stored: {visit_token: 'live-token', expires_at: 1800009999, campaign: {}},
        playerState: {paused: false, ended: false, currentTime: 12, played: timeRanges([[0, 12]])}
    });
    await h.settle();
    assert.equal(h.calls[0].url, '/_cj/analytics/visit');
    assert.equal(h.events().length, 1);
    assert.equal(h.events()[0].event_type, 'video_started');
    assert.equal(h.events()[0].played_seconds, 12);
    h.player.emit('playing');
    await h.settle();
    assert.equal(h.events().length, 1);
});

test('attaching to an already-ended player does not invent a playback start', async () => {
    const h = harness({playerState: {paused: false, ended: true, currentTime: 100}});
    await h.settle();
    assert.equal(h.events().length, 0);
});

test('an explicit new campaign starts a fresh visit instead of inheriting attribution', async () => {
    const h = harness({
        stored: {visit_token: 'previous-campaign-token', expires_at: 1800009999, campaign: {utm_campaign: 'old'}},
        search: '?utm_campaign=new'
    });
    await h.settle();
    assert.equal(h.calls[0].body.visit_token, undefined);
    assert.deepEqual(h.calls[0].body.campaign, {utm_campaign: 'new'});
});

test('the pending queue stays bounded and retains start and end when init is slow', async () => {
    let releaseVisit;
    const h = harness({fetch(call) {
        if (call.url.endsWith('/visit')) return new Promise(resolve => { releaseVisit = resolve; });
        return Promise.resolve(response(204));
    }});
    await h.settle();
    h.player.emit('playing');
    for (let i = 1; i <= 80; i++) {
        h.player.currentTime = i;
        h.player.played = timeRanges([[0, i]]);
        h.player.emit('pause');
    }
    h.player.emit('ended');
    releaseVisit(h.goodVisit());
    for (let i = 0; i < 40; i++) await h.settle();
    assert.equal(h.events().length, 32);
    assert.equal(h.events()[0].event_type, 'video_started');
    assert.equal(h.events().at(-1).event_type, 'video_ended');
});

test('time updates are throttled, while a coverage milestone sends an update', async () => {
    const h = harness();
    await h.settle();
    h.player.emit('playing');
    for (let i = 1; i <= 20; i++) {
        h.player.currentTime = i;
        h.player.played = timeRanges([[0, i]]);
        h.player.emit('timeupdate');
    }
    await h.settle();
    assert.equal(h.events().length, 1);
    h.player.currentTime = 25;
    h.player.played = timeRanges([[0, 25]]);
    h.player.emit('timeupdate');
    await h.settle();
    assert.equal(h.events().at(-1).event_type, 'video_progress');
    assert.equal(h.events().at(-1).played_seconds, 25);
});
