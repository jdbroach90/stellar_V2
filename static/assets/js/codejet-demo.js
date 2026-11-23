/* CodeJet demo conversion experience. Do not treat autoplay as verified interest. */
(function () {
    'use strict';
    var iframe = document.getElementById('stream-player');
    var finished = document.getElementById('demo-video-ended');
    var replay = document.getElementById('demo-replay');
    var contact = document.getElementById('demo-contact');
    var sound = document.getElementById('demo-sound');

    if (iframe && typeof window.Stream === 'function') {
        try {
            var player = window.Stream(iframe);
            window.codejetDemoPlayer = player;  // Read by the existing first-party analytics.
            if (finished && typeof player.addEventListener === 'function') {
                player.addEventListener('ended', function () {
                    finished.hidden = false;
                });
                player.addEventListener('playing', function () {
                    finished.hidden = true;
                });
            }
            if (sound) {
                sound.addEventListener('click', function () {
                    try {
                        player.currentTime = 0;
                        player.muted = false;
                        if (finished) finished.hidden = true;
                        var attempt = player.play();
                        if (attempt && typeof attempt.catch === 'function') {
                            attempt.catch(function () { /* Player controls remain available. */ });
                        }
                    } catch (_) { /* Player controls remain available. */ }
                });
            }
            if (replay) {
                replay.addEventListener('click', function () {
                    if (finished) finished.hidden = true;
                    try {
                        player.currentTime = 0;
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
