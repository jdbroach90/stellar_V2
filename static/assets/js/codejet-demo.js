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
                });
                player.addEventListener('playing', function () {
                    finished.hidden = true;
                });
            }
            // Starting the demo requires an actual click; autoplay is disabled in the embed.
            if (playCover) {
                playCover.addEventListener('click', function () {
                    if (finished) finished.hidden = true;
                    if (playError) playError.hidden = true;
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

    var form = document.querySelector('[data-cj-demo-form]');
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
                            // Use native submit: it does not fire another submit event.
                            form.submit();
                        }).catch(resetAfterFailure);
                } catch (_) { resetAfterFailure(); }
            });
        } catch (_) { resetAfterFailure(); }
    });
}());
