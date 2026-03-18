/**
 * Swipe page: show roommate cards, like/reject via AJAX, load more suggestions.
 * Authors: Maja Spirto 2022/0572, Milica Eva Stojanovic 2022/0361
 */
(function () {
    'use strict';

    const profiles = JSON.parse(document.getElementById('profiles-data').textContent || '[]');
    let currentIndex = 0;
    let isLoadingMore = false;
    let cardMapInstance = null;

    const profileImage = document.getElementById('profileImage');
    const profileName = document.getElementById('profileName');
    const profileSubtitle = document.getElementById('profileSubtitle');
    const housingStatusEl = document.getElementById('housingStatus');
    const housingMoneyEl = document.getElementById('housingMoney');
    const locationLineEl = document.getElementById('locationLine');
    const sectionLifestyle = document.getElementById('sectionLifestyle');
    const lifestyleList = document.getElementById('lifestyleList');
    const sectionPets = document.getElementById('sectionPets');
    const petsContent = document.getElementById('petsContent');
    const sectionInstruments = document.getElementById('sectionInstruments');
    const instrumentsContent = document.getElementById('instrumentsContent');
    const carouselArrows = document.getElementById('carouselArrows');
    const carouselPrev = document.getElementById('carouselPrev');
    const carouselNext = document.getElementById('carouselNext');
    const rejectBtn = document.getElementById('rejectBtn');
    const likeBtn = document.getElementById('likeBtn');
    const matchMessage = document.getElementById('matchMessage');

    const carouselTrack = document.getElementById('carouselTrack');
    const slides = carouselTrack ? Array.from(carouselTrack.querySelectorAll('.card-carousel-slide')) : [];
    let carouselSlideIndex = 0;
    const cardMapWrap = document.getElementById('cardMapWrap');
    const cardAccommodationMapEl = document.getElementById('cardAccommodationMap');

    function destroyCardMap() {
        if (cardMapInstance && cardAccommodationMapEl) {
            try {
                cardMapInstance.remove();
            } catch (e) { /* ignore */ }
            cardMapInstance = null;
        }
    }

    function initCardMap(lat, lon) {
        if (!cardAccommodationMapEl || typeof L === 'undefined') return;
        destroyCardMap();
        cardAccommodationMapEl.innerHTML = '';
        cardAccommodationMapEl.classList.add('leaflet-container');
        cardMapInstance = L.map(cardAccommodationMapEl, { preferCanvas: true }).setView([lat, lon], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(cardMapInstance);
        L.marker([lat, lon]).addTo(cardMapInstance);
        setTimeout(function () {
            if (cardMapInstance) cardMapInstance.invalidateSize();
        }, 100);
    }

    function setCarouselSlide(index, totalSlides) {
        if (totalSlides < 1) return;
        carouselSlideIndex = (index + totalSlides) % totalSlides;
        slides.forEach(function (slide, i) {
            slide.hidden = i !== carouselSlideIndex;
        });
        if (carouselSlideIndex === 1 && totalSlides > 1 && cardMapWrap && !cardMapWrap.hidden) {
            var profile = profiles[currentIndex];
            if (profile && profile.hasAccommodation && profile.accommodationLat != null && profile.accommodationLon != null) {
                initCardMap(profile.accommodationLat, profile.accommodationLon);
            }
        }
    }

    function setupCarousel(profile) {
        var hasAcc = profile && profile.hasAccommodation && (profile.accommodationLat != null && profile.accommodationLon != null);
        var totalSlides = hasAcc ? 2 : 1;

        slides.forEach(function (slide, i) {
            slide.hidden = i >= totalSlides;
        });
        if (cardMapWrap) cardMapWrap.hidden = !hasAcc;

        if (carouselArrows) {
            carouselArrows.hidden = totalSlides <= 1;
        }
        carouselSlideIndex = 0;
        if (carouselPrev) {
            carouselPrev.onclick = function () {
                setCarouselSlide(carouselSlideIndex - 1, totalSlides);
            };
        }
        if (carouselNext) {
            carouselNext.onclick = function () {
                setCarouselSlide(carouselSlideIndex + 1, totalSlides);
            };
        }
        setCarouselSlide(0, totalSlides);
        destroyCardMap();
    }

    function renderEmptyState() {
        var swipeContent = document.getElementById('swipeContent');
        var emptyState = document.getElementById('emptyState');
        if (swipeContent) {
            swipeContent.classList.add('hidden');
            swipeContent.style.display = 'none';
            swipeContent.setAttribute('aria-hidden', 'true');
        }
        if (emptyState) {
            emptyState.classList.remove('hidden');
            emptyState.style.display = '';
        }
        matchMessage.textContent = '';
        destroyCardMap();
    }

    function appendNewProfiles(more) {
        if (!more || !more.length) return 0;
        var existingIds = {};
        for (var j = 0; j < profiles.length; j++) existingIds[profiles[j].id] = true;
        var added = 0;
        for (var i = 0; i < more.length; i++) {
            if (!existingIds[more[i].id]) {
                profiles.push(more[i]);
                existingIds[more[i].id] = true;
                added++;
            }
        }
        return added;
    }

    function fetchMoreSuggestions(onDone) {
        if (isLoadingMore) {
            if (onDone) onDone([]);
            return;
        }
        var url = (typeof window.SWIPE_SUGGESTIONS_URL !== 'undefined' ? window.SWIPE_SUGGESTIONS_URL : '/swipe/suggestions/').replace(/\/?$/, '/');
        isLoadingMore = true;
        fetch(url, { method: 'GET', credentials: 'same-origin', headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) {
                if (!r.ok) return Promise.reject(new Error('HTTP ' + r.status));
                var ct = r.headers.get('Content-Type') || '';
                if (ct.indexOf('application/json') === -1) return Promise.reject(new Error('Not JSON'));
                return r.json();
            })
            .then(function (data) {
                isLoadingMore = false;
                if (onDone) onDone(data.profiles || []);
            })
            .catch(function () {
                isLoadingMore = false;
                if (onDone) onDone([]);
            });
    }

    function renderProfile() {
        if (!profiles.length) {
            renderEmptyState();
            return;
        }
        if (currentIndex >= profiles.length) {
            matchMessage.textContent = 'Loading…';
            if (isLoadingMore) {
                return;
            }
            fetchMoreSuggestions(function (more) {
                matchMessage.textContent = '';
                appendNewProfiles(more);
                if (currentIndex < profiles.length) {
                    renderProfile();
                } else {
                    renderEmptyState();
                }
            });
            return;
        }
        matchMessage.textContent = '';
        var swipeContent = document.getElementById('swipeContent');
        var emptyState = document.getElementById('emptyState');
        if (swipeContent) {
            swipeContent.classList.remove('hidden');
            swipeContent.style.display = '';
            swipeContent.setAttribute('aria-hidden', 'false');
        }
        if (emptyState) {
            emptyState.classList.add('hidden');
            emptyState.style.display = 'none';
        }

        var profile = profiles[currentIndex];
        if (!profile) return;

        if (profileImage) {
            profileImage.src = profile.image || '';
            profileImage.alt = (profile.firstName || '') + ' ' + (profile.lastName || '');
        }
        if (profileName) profileName.textContent = (profile.firstName || '') + ' ' + (profile.lastName || '') + ', ' + (profile.age != null ? profile.age : '');

        var subtitle = profile.status || 'No occupation';
        if (profile.gender && profile.gender !== '\u2014') subtitle += ' \u00b7 ' + profile.gender;
        if (profileSubtitle) profileSubtitle.textContent = subtitle;

        if (housingStatusEl) housingStatusEl.textContent = '\uD83C\uDFE0 ' + (profile.housingLabel || (profile.hasAccommodation ? 'Offers accommodation' : 'Needs Housing'));
        if (housingMoneyEl) {
            if (profile.budgetValue) housingMoneyEl.textContent = 'Budget: ' + profile.budgetValue;
            else if (profile.rentValue) housingMoneyEl.textContent = 'Rent: ' + profile.rentValue;
            else housingMoneyEl.textContent = '';
        }
        if (locationLineEl) locationLineEl.textContent = profile.locationLine || '';

        if (sectionLifestyle && lifestyleList) {
            var lifestyle = profile.lifestyle || [];
            if (lifestyle.length > 0) {
                sectionLifestyle.hidden = false;
                lifestyleList.innerHTML = '';
                lifestyle.forEach(function (item) {
                    var li = document.createElement('li');
                    li.textContent = item.display || (item.label ? item.label + ': ' + (item.value || '') : item.value || '');
                    lifestyleList.appendChild(li);
                });
            } else {
                sectionLifestyle.hidden = true;
                lifestyleList.innerHTML = '';
            }
        }

        if (petsContent) {
            var pets = profile.pets || [];
            if (pets.length > 0) {
                var ul = document.createElement('ul');
                ul.className = 'card-list';
                pets.forEach(function (p) {
                    var li = document.createElement('li');
                    li.textContent = p;
                    ul.appendChild(li);
                });
                petsContent.innerHTML = '';
                petsContent.appendChild(ul);
            } else {
                petsContent.innerHTML = '<p class="card-empty-label">No pets</p>';
            }
        }
        if (instrumentsContent) {
            var instruments = profile.instruments || [];
            if (instruments.length > 0) {
                var ul = document.createElement('ul');
                ul.className = 'card-list';
                instruments.forEach(function (i) {
                    var li = document.createElement('li');
                    li.textContent = i;
                    ul.appendChild(li);
                });
                instrumentsContent.innerHTML = '';
                instrumentsContent.appendChild(ul);
            } else {
                instrumentsContent.innerHTML = '<p class="card-empty-label">No instruments</p>';
            }
        }

        matchMessage.textContent = '';
        setupCarousel(profile);
        if (currentIndex >= profiles.length - 2 && currentIndex < profiles.length) {
            var lenBefore = profiles.length;
            fetchMoreSuggestions(function (more) {
                appendNewProfiles(more);
                if (currentIndex >= lenBefore) {
                    renderProfile();
                }
            });
        }
    }

    function nextProfile() {
        currentIndex += 1;
        renderProfile();
    }

    function sendSwipeAction(targetId, decision, onDone) {
        var url = typeof window.SWIPE_ACTION_URL !== 'undefined' ? window.SWIPE_ACTION_URL : '/swipe-action/';
        var csrf = typeof window.CSRF_TOKEN !== 'undefined' ? window.CSRF_TOKEN : getCookie('csrftoken');
        var payload = JSON.stringify({ target_id: targetId, decision: decision });
        var opts = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf,
                'Accept': 'application/json'
            },
            body: payload,
            credentials: 'same-origin'
        };
        fetch(url, opts)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (onDone) onDone(data);
            })
            .catch(function () {
                if (onDone) onDone({ ok: false });
            });
    }
    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[]\/+^])/g, '\\$1') + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : '';
    }

    if (rejectBtn) {
        rejectBtn.addEventListener('click', function () {
            var profile = profiles.length && currentIndex < profiles.length ? profiles[currentIndex] : null;
            if (profile && profile.id) {
                sendSwipeAction(profile.id, 'reject', function () {
                    matchMessage.textContent = 'Profile skipped.';
                    setTimeout(nextProfile, 250);
                });
            } else {
                matchMessage.textContent = 'Profile skipped.';
                setTimeout(nextProfile, 250);
            }
        });
    }
    if (likeBtn) {
        likeBtn.addEventListener('click', function () {
            var profile = profiles.length && currentIndex < profiles.length ? profiles[currentIndex] : null;
            if (profile && profile.id) {
                sendSwipeAction(profile.id, 'like', function (data) {
                    matchMessage.textContent = data.matched ? "It's a match!" : 'Like sent.';
                    setTimeout(nextProfile, data.matched ? 800 : 350);
                });
            } else {
                matchMessage.textContent = 'Like sent.';
                setTimeout(nextProfile, 350);
            }
        });
    }

    var navBtnMyProfile = document.getElementById('navBtnMyProfile');
    if (navBtnMyProfile) {
        navBtnMyProfile.addEventListener('click', function (e) {
            e.preventDefault();
            window.location.href = navBtnMyProfile.getAttribute('href') || navBtnMyProfile.href;
        });
    }

    renderProfile();
})();
