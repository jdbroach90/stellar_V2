/* CodeJet demo: user-initiated playback with sound; never autoplay. */
(function () {
    'use strict';
    var iframe = document.getElementById('stream-player');
    var finished = document.getElementById('demo-video-ended');
    var replay = document.getElementById('demo-replay');
    var contact = document.getElementById('demo-contact');
    var playCover = document.getElementById('demo-play');
    var playError = document.getElementById('demo-play-error');
    var videoShell = document.getElementById('demo-video-shell');
    var form = document.querySelector('[data-cj-demo-form]');
    var qualifiedInput = form && form.querySelector('[name="demo_qualified_token"]');
    var watchClicked = false;
    var watchClickedAt = 0;
    var watchToken = '';
    var watchQualified = false;
    var watchQualifying = false;
    var watchQualificationPromise = null;

    function watchApi(path, payload) {
        if (typeof window.fetch !== 'function') return Promise.reject(new Error('No fetch'));
        return window.fetch(path, {
            method: 'POST', credentials: 'same-origin', cache: 'no-store',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) throw new Error('Qualification unavailable');
            return response.json();
        });
    }

    function beginWatch() {
        // Called from the real large-Play click, never during page load.
        if (watchClicked) return;
        watchClicked = true;
        watchClickedAt = Date.now();
        watchApi('/demo/watch/start', {}).then(function (result) {
            if (result && typeof result.watch_token === 'string') {
                watchToken = result.watch_token;
                maybeQualifyWatch();
            }
        }).catch(function () { /* A lead can still submit without ad qualification. */ });
    }

    function actualPlayed(player) {
        // Cloudflare's played TimeRanges excludes unplayed portions skipped by
        // seeking. Ended/currentTime alone are not evidence of coverage.
        try {
            var duration = Number(player.duration);
            var ranges = player.played;
            if (!Number.isFinite(duration) || duration < 15 || duration > 14400 ||
                    !ranges || typeof ranges.length !== 'number' || ranges.length > 1000 ||
                    typeof ranges.start !== 'function' || typeof ranges.end !== 'function') return null;
            var played = 0;
            for (var i = 0; i < ranges.length; i += 1) {
                var start = Number(ranges.start(i));
                var end = Number(ranges.end(i));
                if (!Number.isFinite(start) || !Number.isFinite(end) ||
                        start < 0 || end < start || end > duration + 0.1) return null;
                played += end - start;
            }
            played = Math.min(played, duration);
            return {played_seconds: played, duration_seconds: duration};
        } catch (_) { return null; }
    }

    function maybeQualifyWatch() {
        if (!watchClicked || !watchToken || watchQualified || watchQualifying ||
                !qualifiedInput || !window.codejetDemoPlayer ||
                Date.now() - watchClickedAt < 25000) return;
        var metrics = actualPlayed(window.codejetDemoPlayer);
        if (!metrics || metrics.played_seconds / metrics.duration_seconds < 0.50) return;
        watchQualifying = true;
        watchQualificationPromise = watchApi('/demo/watch/qualify', {
            watch_token: watchToken,
            played_seconds: Math.round(metrics.played_seconds * 100) / 100,
            duration_seconds: Math.round(metrics.duration_seconds * 100) / 100
        }).then(function (result) {
            if (result && typeof result.qualified_token === 'string') {
                qualifiedInput.value = result.qualified_token;
                watchQualified = true;
            }
        }).catch(function () { /* The business inquiry remains available. */ })
          .finally(function () { watchQualifying = false; watchQualificationPromise = null; });
    }

    function revealPlayer() {
        // Hide the native iframe play affordance on iOS until the user clicks the
        // full-size poster button, avoiding the double-button Safari overlay.
        if (videoShell && videoShell.classList) videoShell.classList.remove('demo-play-locked');
        if (playCover) playCover.hidden = true;
    }


    if (iframe && typeof window.Stream === 'function') {
        try {
            var player = window.Stream(iframe);
            window.codejetDemoPlayer = player;  // Read by the existing first-party analytics.
            if (playCover) playCover.dataset.playerReady = 'true';
            if (finished && typeof player.addEventListener === 'function') {
                player.addEventListener('ended', function () {
                    finished.hidden = false;
                    maybeQualifyWatch();
                });
                player.addEventListener('playing', function () {
                    finished.hidden = true;
                });
            }
            player.addEventListener('timeupdate', maybeQualifyWatch);
            player.addEventListener('pause', maybeQualifyWatch);
            // Starting the demo requires an actual click; autoplay is disabled in the embed.
            if (playCover) {
                playCover.addEventListener('click', function () {
                    if (finished) finished.hidden = true;
                    if (playError) playError.hidden = true;
                    beginWatch();
                    revealPlayer(); // reveal native controls if SDK playback is rejected
                    try {
                        player.currentTime = 0;
                        player.muted = false;
                        var attempt = player.play();
                        if (attempt && typeof attempt.catch === 'function') {
                            attempt.catch(function () {
                                if (playError) playError.hidden = false;
                            });
                        }
                    } catch (_) {
                        if (playError) playError.hidden = false;
                    }
                });
            }
            if (replay) {
                replay.addEventListener('click', function () {
                    if (finished) finished.hidden = true;
                    try {
                        player.currentTime = 0;
                        player.muted = false;
                        var attempt = player.play();
                        if (attempt && typeof attempt.catch === 'function') {
                            attempt.catch(function () { if (finished) finished.hidden = false; });
                        }
                    } catch (_) {
                        if (finished) finished.hidden = false;
                    }
                });
            }
        } catch (_) {
            // The embed must still work if the optional player SDK is unavailable.
        }
    }

    // When the SDK is unavailable, a click reveals the embedded native controls.
    if (playCover && !playCover.dataset.playerReady) {
        playCover.addEventListener('click', function () {
            revealPlayer();
            if (playError) playError.hidden = false;
        });
    }

    // End-of-video and other CTAs scroll to the form instead of sending people
    // away to a different page. The form also remains visible while playing.
    var actionLinks = document.querySelectorAll('a[href="#demo-contact"]');
    Array.prototype.forEach.call(actionLinks, function (link) {
        link.addEventListener('click', function () {
            if (contact) contact.classList.add('demo-contact-highlight');
        });
    });

    if (!form) return;
    var button = form.querySelector('[type="submit"]');
    var captcha = form.querySelector('[name="g-recaptcha-response"]');
    var error = form.querySelector('.demo-form-error');
    var siteKey = form.getAttribute('data-site-key') || '';
    var submitting = false;

    function resetAfterFailure() {
        submitting = false;
        if (button) button.disabled = false;
        if (captcha) captcha.value = '';
        if (error) error.hidden = false;
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (submitting) return;
        if (error) error.hidden = true;
        maybeQualifyWatch();
        if (!button || !captcha || !siteKey || !window.grecaptcha ||
                typeof window.grecaptcha.execute !== 'function' ||
                typeof window.grecaptcha.ready !== 'function') {
            resetAfterFailure();
            return;
        }
        submitting = true;
        button.disabled = true;
        try {
            window.grecaptcha.ready(function () {
                try {
                    window.grecaptcha.execute(siteKey, { action: 'submit' })
                        .then(function (token) {
                            if (!token) { resetAfterFailure(); return; }
                            captcha.value = token;
                            // If the viewer just crossed 50%, allow the first-party
                            // qualification response to arrive before native submit.
                            // Never block an ordinary inquiry on optional marketing.
                            var pending = watchQualificationPromise;
                            if (pending && typeof window.setTimeout === 'function') {
                                Promise.race([
                                    pending, new Promise(function (resolve) {
                                        window.setTimeout(resolve, 1500);
                                    })
                                ]).then(function () { form.submit(); }, function () { form.submit(); });
                            } else {
                                form.submit();
                            }
                        }).catch(resetAfterFailure);
                } catch (_) { resetAfterFailure(); }
            });
        } catch (_) { resetAfterFailure(); }
    });
}());
