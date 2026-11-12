/* First-party demo telemetry. Playback and navigation never depend on this file. */
(function () {
    'use strict';

    try {
        var tag = document.querySelector('script[data-cj-analytics]');
        if (!tag || window.codejetAnalyticsLoaded || typeof window.fetch !== 'function') return;
        if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' ||
                window.doNotTrack === '1') return;
        var page = tag.getAttribute('data-cj-page');
        if (page !== '/' && page !== '/demo') return;
        if (!window.crypto || typeof window.crypto.getRandomValues !== 'function') return;
        window.codejetAnalyticsLoaded = true;

        var STORAGE_KEY = 'codejet_demo_visit_v1';
        var UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
        var MAX_PENDING = 32;
        var MAX_SECONDS = 86400;
        var videoId = tag.getAttribute('data-cj-video-id') || '';
        var pending = [];
        var flushing = false;
        var renewing = false;
        var token = null;
        var tokenExpiry = 0;
        var initPromise = null;
        var leaving = false;
        var retryScheduled = false;

        function uuid() {
            if (typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
            var bytes = new Uint8Array(16);
            window.crypto.getRandomValues(bytes);
            bytes[6] = (bytes[6] & 15) | 64;
            bytes[8] = (bytes[8] & 63) | 128;
            var hex = Array.from(bytes, function (b) { return b.toString(16).padStart(2, '0'); }).join('');
            return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' +
                hex.slice(16, 20) + '-' + hex.slice(20);
        }

        function expiresMs(value) {
            if (typeof value === 'number') return value < 1000000000000 ? value * 1000 : value;
            return typeof value === 'string' ? Date.parse(value) : 0;
        }

        function cleanCampaign(input) {
            var result = {};
            UTM_KEYS.forEach(function (key) {
                if (input && typeof input[key] === 'string') {
                    var value = input[key].replace(/[\x00-\x1f\x7f]/g, '').trim().slice(0, 100);
                    if (value) result[key] = value;
                }
            });
            return result;
        }

        var stored = null;
        try {
            stored = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || 'null');
        } catch (_) { /* Blocked storage still permits this page's in-memory visit. */ }
        var parameters = new URLSearchParams(window.location.search);
        var incoming = {};
        UTM_KEYS.forEach(function (key) {
            if (parameters.has(key)) incoming[key] = parameters.get(key);
        });
        incoming = cleanCampaign(incoming);
        var cachedSessionLive = Boolean(stored && typeof stored === 'object' && !Array.isArray(stored) &&
            typeof stored.visit_token === 'string' && stored.visit_token.length > 0 &&
            stored.visit_token.length <= 512 && Number.isFinite(expiresMs(stored.expires_at)) &&
            expiresMs(stored.expires_at) > Date.now());
        // Attribution expires with its visit; a restored tab is not a new mailer scan.
        var savedCampaign = cachedSessionLive ? cleanCampaign(stored.campaign) : {};
        var explicitCampaign = Object.keys(incoming).length > 0;
        var campaignChanged = explicitCampaign && JSON.stringify(incoming) !== JSON.stringify(savedCampaign);
        var campaign = explicitCampaign ? incoming : savedCampaign;
        if (cachedSessionLive && !campaignChanged) {
            token = stored.visit_token;
            tokenExpiry = expiresMs(stored.expires_at);
        }

        var referrerHost = '';
        try { referrerHost = new URL(document.referrer).hostname.slice(0, 253); } catch (_) { /* No referrer. */ }

        function requestJson(path, data) {
            // Same-origin only. A browser never supplies an IP or any server/admin secret.
            var controller = typeof AbortController === 'function' ? new AbortController() : null;
            var timeout = controller ? window.setTimeout(function () { controller.abort(); }, 8000) : null;
            return Promise.resolve().then(function () {
                return window.fetch(path, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data),
                    cache: 'no-store',
                    keepalive: true,
                    signal: controller ? controller.signal : undefined
                });
            }).finally(function () { if (timeout !== null) window.clearTimeout(timeout); });
        }

        function rememberVisit(data) {
            token = data.visit_token;
            tokenExpiry = expiresMs(data.expires_at);
            try {
                window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                    visit_token: token,
                    visit_id: data.visit_id,
                    expires_at: data.expires_at,
                    campaign: campaign
                }));
            } catch (_) { /* No persistent browser storage is required. */ }
        }

        function initialise(forceNew) {
            if (initPromise) return initPromise;
            if (forceNew || tokenExpiry <= Date.now()) {
                if (token) campaign = explicitCampaign ? incoming : {};
                token = null;
                tokenExpiry = 0;
            }
            var body = {event_id: uuid(), page: page, campaign: campaign, referrer_host: referrerHost};
            if (token) body.visit_token = token;
            var attempt = 0;
            async function send() {
                attempt += 1;
                try {
                    var response = await requestJson('/_cj/analytics/visit', body);
                    if (response.status === 204) return false;
                    if (response.status === 401 && body.visit_token && attempt < 2) {
                        token = null;
                        tokenExpiry = 0;
                        delete body.visit_token;
                        // Server rejection also invalidates attribution inherited from that visit.
                        campaign = explicitCampaign ? incoming : {};
                        body.campaign = campaign;
                        try { window.sessionStorage.removeItem(STORAGE_KEY); } catch (_) {}
                        return send();
                    }
                    if (!response.ok) {
                        var error = new Error('Telemetry unavailable');
                        error.retryable = response.status >= 500;
                        throw error;
                    }
                    var data = await response.json();
                    if (!data || typeof data.visit_token !== 'string' || data.visit_token.length > 512 ||
                            !Number.isFinite(expiresMs(data.expires_at)) || expiresMs(data.expires_at) <= Date.now()) {
                        throw new Error('Invalid telemetry response');
                    }
                    rememberVisit(data);
                    return true;
                } catch (error) {
                    if (attempt < 2 && error.retryable !== false && !leaving) {
                        return new Promise(function (resolve) { window.setTimeout(resolve, 1000); }).then(send);
                    }
                    return false;
                }
            }
            initPromise = send().finally(function () { initPromise = null; });
            return initPromise;
        }

        function scheduleRetry() {
            if (retryScheduled || leaving) return;
            retryScheduled = true;
            window.setTimeout(function () {
                retryScheduled = false;
                flush();
            }, 1000);
        }

        function flush() {
            if (flushing || !token || !pending.length || initPromise) return;
            if (tokenExpiry <= Date.now()) {
                if (!renewing) {
                    renewing = true;
                    initialise(true).then(function (ok) {
                        renewing = false;
                        if (ok) flush();
                    });
                }
                return;
            }
            flushing = true;
            var item = pending[0];
            var body = Object.assign({}, item.body, {visit_token: token});
            item.attempts += 1;
            requestJson('/_cj/analytics/event', body).then(function (response) {
                if ((response.status === 401 || response.status === 410) && !item.renewed && !leaving) {
                    item.renewed = true;
                    return initialise(true).then(function () {});
                }
                if (response.ok || (response.status < 500 && response.status !== 429) || item.attempts >= 2) {
                    if (pending[0] === item) pending.shift();
                } else {
                    scheduleRetry();
                }
            }).catch(function () {
                if (item.attempts >= 2) {
                    if (pending[0] === item) pending.shift();
                } else {
                    scheduleRetry();
                }
            }).finally(function () {
                flushing = false;
                if (!retryScheduled) flush();
            });
        }

        function enqueue(type, metrics) {
            if (pending.length >= MAX_PENDING) {
                var expendable = pending.findIndex(function (item) { return item.body.event_type === 'video_progress'; });
                if (expendable >= 0) pending.splice(expendable, 1);
                else return;
            }
            pending.push({attempts: 0, body: Object.assign({
                event_id: uuid(),
                event_type: type,
                page: '/demo',
                video_id: videoId
            }, metrics)});
            flush();
        }

        function sendPendingOnExit() {
            // Duplicate in-flight deliveries reuse event IDs; the server deduplicates them.
            // The bounded queue fits within the browser's keepalive request budget.
            if (!token || tokenExpiry <= Date.now()) return;
            pending.slice().forEach(function (item) {
                requestJson('/_cj/analytics/event', Object.assign({}, item.body, {visit_token: token})).catch(function () {});
            });
        }

        function metric(value, allowZero) {
            return typeof value === 'number' && Number.isFinite(value) &&
                value >= (allowZero ? 0 : Number.MIN_VALUE) && value <= MAX_SECONDS ?
                Math.round(value * 1000) / 1000 : null;
        }

        function attachPlayer(player) {
            if (!player || typeof player.addEventListener !== 'function') return;
            var started = false;
            var ended = false;
            var seeking = false;
            var lastProgressAt = Date.now();
            var lastProgressSignature = '';
            var reached = 0;
            var milestones = [25, 50, 75, 90];

            function snapshot() {
                var position = null;
                var duration = null;
                var played = null;
                try { position = metric(player.currentTime, true); } catch (_) {}
                try { duration = metric(player.duration, false); } catch (_) {}
                try {
                    var ranges = player.played;
                    if (ranges && Number.isInteger(ranges.length) && ranges.length >= 0 && ranges.length <= 1000 &&
                            typeof ranges.start === 'function' && typeof ranges.end === 'function') {
                        var total = 0;
                        for (var i = 0; i < ranges.length; i += 1) {
                            var start = metric(ranges.start(i), true);
                            var finish = metric(ranges.end(i), true);
                            if (start === null || finish === null || finish < start) throw new Error('Invalid played range');
                            total += finish - start;
                        }
                        played = metric(duration === null ? total : Math.min(total, duration), true);
                    }
                } catch (_) { played = null; }
                return {position_seconds: position, duration_seconds: duration, played_seconds: played};
            }

            function progress(force) {
                if (!started || ended || seeking) return;
                var metrics = snapshot();
                var signature = JSON.stringify(metrics);
                if (signature === lastProgressSignature) return;
                var coverage = metrics.duration_seconds && metrics.played_seconds !== null ?
                    100 * metrics.played_seconds / metrics.duration_seconds : null;
                var next = reached;
                while (next < milestones.length && coverage !== null && coverage >= milestones[next]) next += 1;
                if (!force && next === reached && Date.now() - lastProgressAt < 15000) return;
                reached = next;
                lastProgressAt = Date.now();
                lastProgressSignature = signature;
                enqueue('video_progress', metrics);
            }

            function on(name, action) {
                player.addEventListener(name, function () {
                    try { action(); } catch (_) { /* Telemetry must never interrupt the player. */ }
                });
            }
            function recordStart() {
                if (!started) {
                    started = true;
                    lastProgressAt = Date.now();
                    enqueue('video_started', snapshot());
                }
            }
            on('playing', recordStart);
            on('timeupdate', function () { progress(false); });
            on('pause', function () { progress(true); });
            on('seeking', function () { seeking = true; });
            on('seeked', function () { seeking = false; });
            on('ended', function () {
                if (ended) return;
                ended = true;
                enqueue('video_ended', snapshot());
                sendPendingOnExit();
            });
            document.addEventListener('visibilitychange', function () {
                if (document.visibilityState === 'hidden') {
                    try { progress(true); sendPendingOnExit(); } catch (_) {}
                }
            });
            window.addEventListener('pagehide', function () {
                leaving = true;
                try { progress(true); sendPendingOnExit(); } catch (_) {}
            });
            // A slow script download may attach after the player emitted its first playing event.
            try {
                if (player.paused === false && player.ended !== true) recordStart();
            } catch (_) { /* Wait for a player event if the SDK state is not ready. */ }
        }

        var initialized = initialise(false);
        if (page === '/demo' && videoId) attachPlayer(window.codejetDemoPlayer);
        initialized.then(function (ok) { if (ok) flush(); });
    } catch (_) {
        // Analytics is optional; the page and Cloudflare player remain usable.
    }
}());
