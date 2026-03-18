/**
 * Create profile form: multi-step UI, validation, conditional fields.
 * Authors: Jovana Ceganjac 2022/0423, Milica Eva Stojanovic 2022/0361
 */
(function () {
    'use strict';

    var hasAccommodationYes = document.getElementById('hasAccommodationYes');
    var hasAccommodationNo = document.getElementById('hasAccommodationNo');
    var accommodationDetails = document.getElementById('accommodationDetails');

    var hasPetYes = document.getElementById('hasPetYes');
    var hasPetNo = document.getElementById('hasPetNo');
    var hasPetDetails = document.getElementById('hasPetDetails');

    var hasPartiesYes = document.getElementById('hasPartiesYes');
    var hasPartiesNo = document.getElementById('hasPartiesNo');
    var partyFrequencyBlock = document.getElementById('partyFrequencyBlock');

    var playsInstrumentYes = document.getElementById('playsInstrumentYes');
    var playsInstrumentNo = document.getElementById('playsInstrumentNo');
    var instrumentDetails = document.getElementById('instrumentDetails');

    function toggleBlock(show, block) {
        if (!block) return;
        block.hidden = !show;
    }

    var accommodationPreferencesSection = document.getElementById('accommodationPreferencesSection');
    var roommateHasAccommodationBlock = document.getElementById('roommateHasAccommodationBlock');

    function onAccommodationChange() {
        toggleBlock(hasAccommodationYes && hasAccommodationYes.checked, accommodationDetails);

        var sectionPrefs = document.getElementById('sectionAccommodationPreferences');
        if (sectionPrefs) sectionPrefs.hidden = hasAccommodationYes && hasAccommodationYes.checked;

        // When user has accommodation, show accommodation details and init/refresh map
        if (hasAccommodationYes && hasAccommodationYes.checked) {
            var editBlock = document.getElementById('profileEditBlock');
            if (!(editBlock && editBlock.hidden)) {
                scheduleAccommodationMapInitOrRefresh();
            }
        }

        // When user switches to "No" (no accommodation), preferred location section becomes visible
        var prefsSectionVisible = (sectionPrefs && !sectionPrefs.hidden) || (accommodationPreferencesSection && !accommodationPreferencesSection.hidden);
        if ((!hasAccommodationYes || !hasAccommodationYes.checked) && prefsSectionVisible) {
            schedulePreferredMapInitOrRefresh();
        }

        // Hide whole Accommodation Preferences section when user has accommodation
        if (accommodationPreferencesSection) {
            accommodationPreferencesSection.hidden = hasAccommodationYes && hasAccommodationYes.checked;
        }

        // Hide "Should the roommate have accommodation?" when user has accommodation
        if (roommateHasAccommodationBlock) {
            roommateHasAccommodationBlock.hidden = hasAccommodationYes && hasAccommodationYes.checked;
        }

        var cityInput = document.getElementById('city');
        if (cityInput) cityInput.required = !(hasAccommodationYes && hasAccommodationYes.checked);
    }

    function onPetChange() {
        toggleBlock(hasPetYes && hasPetYes.checked, hasPetDetails);
    }

    function onPartiesChange() {
        toggleBlock(hasPartiesYes && hasPartiesYes.checked, partyFrequencyBlock);
    }

    function onInstrumentChange() {
        toggleBlock(playsInstrumentYes && playsInstrumentYes.checked, instrumentDetails);
    }

    if (hasAccommodationYes) hasAccommodationYes.addEventListener('change', onAccommodationChange);
    if (hasAccommodationNo) hasAccommodationNo.addEventListener('change', onAccommodationChange);
    if (hasPetYes) hasPetYes.addEventListener('change', onPetChange);
    if (hasPetNo) hasPetNo.addEventListener('change', onPetChange);
    if (hasPartiesYes) hasPartiesYes.addEventListener('change', onPartiesChange);
    if (hasPartiesNo) hasPartiesNo.addEventListener('change', onPartiesChange);
    if (playsInstrumentYes) playsInstrumentYes.addEventListener('change', onInstrumentChange);
    if (playsInstrumentNo) playsInstrumentNo.addEventListener('change', onInstrumentChange);

    function updateBudgetRequired() {
        var budgetInput = document.getElementById('budget');
        if (budgetInput) budgetInput.required = hasAccommodationNo && hasAccommodationNo.checked;
    }

    // Profile photo: preview when user selects an image
    var profilePhotoInput = document.getElementById('profilePhoto');
    var profilePhotoPreview = document.getElementById('profilePhotoPreview');
    var profilePhotoImg = document.getElementById('profilePhotoImg');
    var profilePhotoPlaceholder = document.getElementById('profilePhotoPlaceholder');

    if (profilePhotoInput && profilePhotoPreview && profilePhotoImg && profilePhotoPlaceholder) {
        profilePhotoInput.addEventListener('change', function () {
            var file = this.files && this.files[0];
            if (file && file.type.indexOf('image/') === 0) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    profilePhotoImg.src = e.target.result;
                    profilePhotoImg.hidden = false;
                    profilePhotoPlaceholder.hidden = true;
                    profilePhotoPreview.classList.add('has-image');
                };
                reader.readAsDataURL(file);
            } else {
                var initialSrc = profilePhotoPreview.getAttribute('data-initial-src') || '';
                if (initialSrc) {
                    profilePhotoImg.src = initialSrc;
                    profilePhotoImg.hidden = false;
                    profilePhotoPlaceholder.hidden = true;
                    profilePhotoPreview.classList.add('has-image');
                } else {
                    profilePhotoImg.src = '';
                    profilePhotoImg.hidden = true;
                    profilePhotoPlaceholder.hidden = false;
                    profilePhotoPreview.classList.remove('has-image');
                }
            }
        });
    }

    // Date of birth: calendar picker
    var dateOfBirthEl = document.getElementById('dateOfBirth');
    if (dateOfBirthEl && typeof flatpickr !== 'undefined') {
        flatpickr(dateOfBirthEl, {
            allowInput: true,
            dateFormat: 'd.m.Y',
            disableMobile: true,
            className: 'datepicker-calendar-zimmer'
        });
    }

    var accommodationMapEl = document.getElementById('accommodationMap');
    var accommodationAddressInput = document.getElementById('accommodationAddress');
    var showAccommodationOnMapBtn = document.getElementById('showAccommodationOnMap');
    window.accommodationMapInstance = null;
    var accommodationMarker = null;

    var preferredMapEl = document.getElementById('preferredLocationMap');
    var preferredLocationInput = document.getElementById('preferredLocation');
    var locationRadiusInput = document.getElementById('locationRadius');
    var preferredMapInstance = null;
    var preferredMarker = null;
    var preferredCircle = null;

    function isMapContainerVisible(el) {
        return !!(el && el.offsetParent !== null && el.offsetWidth > 0 && el.offsetHeight > 0);
    }

    function initAccommodationMap(forceInitWhenJustShown) {
        if (!accommodationMapEl || typeof L === 'undefined' || window.accommodationMapInstance) return;
        if (!forceInitWhenJustShown && !isMapContainerVisible(accommodationMapEl)) return;

        var latEl = document.getElementById('accommodationLat');
        var lonEl = document.getElementById('accommodationLon');
        var defaultLat = 44.8176;
        var defaultLon = 20.4633;

        if (latEl && lonEl && latEl.value && lonEl.value) {
            var lat = parseFloat(latEl.value);
            var lon = parseFloat(lonEl.value);
            if (!isNaN(lat) && !isNaN(lon)) {
                defaultLat = lat;
                defaultLon = lon;
            }
        }

        accommodationMapEl.textContent = '';

        window.accommodationMapInstance = L.map('accommodationMap', { preferCanvas: true })
            .setView([defaultLat, defaultLon], latEl && latEl.value ? 16 : 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(window.accommodationMapInstance);

        accommodationMapEl.classList.add('leaflet-container');

        if (
            latEl && lonEl &&
            latEl.value && lonEl.value &&
            !isNaN(parseFloat(latEl.value)) &&
            !isNaN(parseFloat(lonEl.value))
        ) {
            accommodationMarker = L.marker([
                parseFloat(latEl.value),
                parseFloat(lonEl.value)
            ]).addTo(window.accommodationMapInstance);
        }

        window.accommodationMapInstance.on('click', function (e) {
            var ll = e.latlng;
            if (accommodationMarker) window.accommodationMapInstance.removeLayer(accommodationMarker);
            accommodationMarker = L.marker([ll.lat, ll.lng]).addTo(window.accommodationMapInstance);
            if (latEl) latEl.value = ll.lat;
            if (lonEl) lonEl.value = ll.lng;
        });
    }

    function scheduleAccommodationMapInitOrRefresh() {
        var mapEl = document.getElementById('accommodationMap');
        if (!mapEl || typeof L === 'undefined') return;

        function tryInitOrRefresh() {
            if (mapEl.offsetWidth > 0 && mapEl.offsetHeight > 0) {
                if (!window.accommodationMapInstance) {
                    initAccommodationMap(true);
                }

                var m = window.accommodationMapInstance;
                if (m && typeof m.invalidateSize === 'function') {
                    var c = typeof m.getCenter === 'function' ? m.getCenter() : null;
                    var z = typeof m.getZoom === 'function' ? m.getZoom() : null;

                    m.invalidateSize();

                    if (c && typeof z === 'number') {
                        m.setView([c.lat, c.lng], z, { animate: false });
                    }

                    setTimeout(function () {
                        try {
                            m.invalidateSize();
                            if (c && typeof z === 'number') {
                                m.setView([c.lat, c.lng], z, { animate: false });
                            }
                        } catch (e) {}
                    }, 150);

                    setTimeout(function () {
                        try {
                            m.invalidateSize();
                        } catch (e) {}
                    }, 400);
                }

                return true;
            }
            return false;
        }

        if (tryInitOrRefresh()) return;

        requestAnimationFrame(function () {
            if (tryInitOrRefresh()) return;
            setTimeout(function () {
                tryInitOrRefresh();
            }, 150);
        });
    }

    function geocodeAddress(address, city, done) {
        var query = [address, city].filter(Boolean).join(', ') || address || city;
        if (!query.trim()) {
            done(new Error('Enter address or city'));
            return;
        }
        var url = 'https://nominatim.openstreetmap.org/search?format=json&q=' + encodeURIComponent(query) + '&limit=1';
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.setRequestHeader('Accept-Language', 'en');
        xhr.setRequestHeader('User-Agent', 'ZimmerRoommateApp/1.0');
        xhr.onload = function () {
            if (xhr.status !== 200) {
                done(new Error('Geocoding failed'));
                return;
            }
            var data = JSON.parse(xhr.responseText);
            if (data && data[0]) {
                done(null, { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) });
            } else {
                done(new Error('Address not found'));
            }
        };
        xhr.onerror = function () {
            done(new Error('Network error'));
        };
        xhr.send();
    }

    function geocodeCityThenProceed(cityName, done) {
        if (!cityName || !cityName.trim()) {
            done(null);
            return;
        }
        geocodeAddress('', cityName.trim(), function (err, coords) {
            if (!err && coords) {
                done(coords);
                return;
            }
            geocodeAddress('', cityName.trim() + ', Serbia', function (err2, coords2) {
                done((!err2 && coords2) ? coords2 : null);
            });
        });
    }

    if (showAccommodationOnMapBtn && accommodationAddressInput) {
        showAccommodationOnMapBtn.addEventListener('click', function () {
            var cityEl = document.getElementById('city');
            var city = cityEl ? cityEl.value.trim() : '';
            var address = accommodationAddressInput.value.trim();

            if (!address && !city) {
                alert('Please enter your accommodation address or city.');
                return;
            }

            if (!window.accommodationMapInstance) {
                initAccommodationMap(true);
            }
            scheduleAccommodationMapInitOrRefresh();

            showAccommodationOnMapBtn.disabled = true;
            showAccommodationOnMapBtn.textContent = 'Searching...';

            geocodeAddress(address, city, function (err, coords) {
                showAccommodationOnMapBtn.disabled = false;
                showAccommodationOnMapBtn.textContent = 'Show on map';

                if (err) {
                    alert(err.message || 'Could not find location.');
                    return;
                }

                var map = window.accommodationMapInstance;
                if (!map) return;

                setTimeout(function () {
                    try {
                        map.invalidateSize();
                    } catch (e) {}

                    map.setView([coords.lat, coords.lon], 16);

                    if (accommodationMarker) map.removeLayer(accommodationMarker);
                    accommodationMarker = L.marker([coords.lat, coords.lon]).addTo(map);

                    var latEl = document.getElementById('accommodationLat');
                    var lonEl = document.getElementById('accommodationLon');
                    if (latEl) latEl.value = coords.lat;
                    if (lonEl) lonEl.value = coords.lon;
                }, 50);
            });
        });
    }

    function updatePreferredRadiusCircle() {
        if (!preferredMapInstance || !preferredMarker) return;

        var radiusKm = parseFloat(locationRadiusInput && locationRadiusInput.value) || 0;
        if (preferredCircle) {
            preferredMapInstance.removeLayer(preferredCircle);
            preferredCircle = null;
        }
        if (radiusKm > 0) {
            var latLng = preferredMarker.getLatLng();
            preferredCircle = L.circle(latLng, {
                radius: radiusKm * 1000,
                color: '#e85d04',
                fillColor: '#e85d04',
                fillOpacity: 0.15,
                weight: 2
            }).addTo(preferredMapInstance);
        }
    }

    var radiusUpdateTimeout = null;
    function debouncedUpdatePreferredRadiusCircle() {
        if (radiusUpdateTimeout) clearTimeout(radiusUpdateTimeout);
        radiusUpdateTimeout = setTimeout(function () {
            radiusUpdateTimeout = null;
            updatePreferredRadiusCircle();
        }, 150);
    }

    function initPreferredLocationMap(forceInitWhenJustShown) {
        if (!preferredMapEl || typeof L === 'undefined' || preferredMapInstance) return;
        if (!forceInitWhenJustShown && !isMapContainerVisible(preferredMapEl)) return;

        preferredMapEl.textContent = '';
        preferredMapInstance = L.map('preferredLocationMap', { preferCanvas: true }).setView([44.8176, 20.4633], 10);
        window.preferredMapInstance = preferredMapInstance;

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(preferredMapInstance);

        preferredMapEl.classList.add('leaflet-container');

        preferredMapInstance.on('click', function (e) {
            var lat = e.latlng.lat;
            var lon = e.latlng.lng;

            if (preferredMarker) preferredMapInstance.removeLayer(preferredMarker);
            if (preferredCircle) {
                preferredMapInstance.removeLayer(preferredCircle);
                preferredCircle = null;
            }

            preferredMarker = L.marker([lat, lon]).addTo(preferredMapInstance);

            if (preferredLocationInput) preferredLocationInput.value = lat.toFixed(5) + ', ' + lon.toFixed(5);

            var cityLatEl = document.getElementById('cityLat');
            var cityLonEl = document.getElementById('cityLon');
            if (cityLatEl) cityLatEl.value = lat;
            if (cityLonEl) cityLonEl.value = lon;

            updatePreferredRadiusCircle();
        });

        if (locationRadiusInput) {
            locationRadiusInput.addEventListener('input', debouncedUpdatePreferredRadiusCircle);
            locationRadiusInput.addEventListener('change', updatePreferredRadiusCircle);
        }
    }

    function schedulePreferredMapInitOrRefresh() {
        var prefMap = document.getElementById('preferredLocationMap');
        if (!prefMap || typeof L === 'undefined') return;

        function tryInitOrRefresh() {
            if (prefMap.offsetWidth > 0 && prefMap.offsetHeight > 0) {
                if (!window.preferredMapInstance) {
                    if (typeof window.zimmerInitPreferredMap === 'function') {
                        window.zimmerInitPreferredMap(true);
                    }
                }

                var m = window.preferredMapInstance;
                if (m && typeof m.invalidateSize === 'function') {
                    var c = m.getCenter();
                    var z = m.getZoom();

                    m.invalidateSize();

                    if (c) m.setView([c.lat, c.lng], z, { animate: false });

                    setTimeout(function () {
                        m.invalidateSize();
                        if (c) m.setView([c.lat, c.lng], z, { animate: false });
                    }, 150);

                    setTimeout(function () {
                        m.invalidateSize();
                    }, 400);
                }
                return true;
            }
            return false;
        }

        if (tryInitOrRefresh()) return;
        requestAnimationFrame(function () {
            if (tryInitOrRefresh()) return;
            setTimeout(function () {
                tryInitOrRefresh();
            }, 150);
        });
    }

    if (preferredMapEl && typeof L !== 'undefined') {
        if (isMapContainerVisible(preferredMapEl)) {
            initPreferredLocationMap();
        }
        window.zimmerInitPreferredMap = function (force) {
            if (!window.preferredMapInstance) {
                initPreferredLocationMap(!!force);
            } else {
                schedulePreferredMapInitOrRefresh();
            }
        };
    }

    // ----- Next / Back: switch between Part 1 and Part 2 -----
    var formPart1 = document.getElementById('formPart1');
    var formPart2 = document.getElementById('formPart2');
    var btnNext = document.getElementById('btnNext');
    var btnBack = document.getElementById('btnBack');

    var sectionErrorIds = ['validationMessageBasic', 'validationMessageAbout', 'validationMessageAccommodation', 'validationMessageRoommate'];

    function hideAllSectionErrors() {
        sectionErrorIds.forEach(function (id) {
            var el = document.getElementById(id);
            if (el) {
                el.hidden = true;
                el.textContent = '';
            }
        });
    }

    function showSectionError(sectionId, message) {
        hideAllSectionErrors();
        var el = document.getElementById(sectionId);
        if (el) {
            el.textContent = message;
            el.hidden = false;
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // Returns { section, message } for first error, or null if valid
    function validatePart1WithSection() {
        var firstName = document.getElementById('firstName');
        var lastName = document.getElementById('lastName');
        var phone = document.getElementById('phone');
        var idNumber = document.getElementById('idNumber');
        var dateOfBirth = document.getElementById('dateOfBirth');
        var city = document.getElementById('city');
        var occupation = document.getElementById('occupation');
        var profilePhoto = document.getElementById('profilePhoto');

        if (!firstName || !firstName.value.trim()) return { section: 'validationMessageBasic', message: 'All required fields must be filled in.' };
        if (!lastName || !lastName.value.trim()) return { section: 'validationMessageBasic', message: 'All required fields must be filled in.' };
        if (!phone || !phone.value.trim()) return { section: 'validationMessageBasic', message: 'All required fields must be filled in.' };
        if (!idNumber || !idNumber.value.trim()) return { section: 'validationMessageBasic', message: 'All required fields must be filled in.' };
        if (!dateOfBirth || !dateOfBirth.value.trim()) return { section: 'validationMessageBasic', message: 'All required fields must be filled in.' };

        if (!hasAccommodationYes || !hasAccommodationYes.checked) {
            if (!city || !city.value.trim()) return { section: 'validationMessageAccommodation', message: 'City is required when you are looking for accommodation.' };
        }

        var previewEl = document.getElementById('profilePhotoPreview');
        var hasExistingPhoto = previewEl && (previewEl.getAttribute('data-initial-src') || '').trim();
        if (!hasExistingPhoto && (!profilePhoto || !profilePhoto.files || profilePhoto.files.length === 0)) {
            return { section: 'validationMessageBasic', message: 'Profile photo is required.' };
        }

        if (hasAccommodationNo && hasAccommodationNo.checked) {
            var budgetEl = document.getElementById('budget');
            if (!budgetEl || !budgetEl.value.trim()) return { section: 'validationMessageBasic', message: 'Budget (EUR) is required when you are looking for accommodation.' };
            if (parseFloat(budgetEl.value) < 1) return { section: 'validationMessageBasic', message: 'Budget (EUR) must be greater than 0 when you are looking for accommodation.' };
        }

        var nameCityRe = /^[a-zA-Z\s\-]+$/;
        if (firstName && firstName.value.trim() && !nameCityRe.test(firstName.value.trim())) return { section: 'validationMessageBasic', message: 'First name must contain only letters, spaces, or hyphens.' };
        if (lastName && lastName.value.trim() && !nameCityRe.test(lastName.value.trim())) return { section: 'validationMessageBasic', message: 'Last name must contain only letters, spaces, or hyphens.' };
        if (occupation && occupation.value.trim() && !nameCityRe.test(occupation.value.trim())) return { section: 'validationMessageBasic', message: 'Occupation must contain only letters, spaces, or hyphens.' };
        if (!hasAccommodationYes || !hasAccommodationYes.checked) {
            if (city && city.value.trim() && !nameCityRe.test(city.value.trim())) return { section: 'validationMessageAccommodation', message: 'City must contain only letters, spaces, or hyphens.' };
        }
        if (phone && phone.value.trim() && !/^\+38\d{9,10}$/.test(phone.value.trim())) return { section: 'validationMessageBasic', message: 'Phone must be +38 followed by 9 or 10 digits.' };
        if (idNumber && idNumber.value.trim() && !/^\d{13}$/.test(idNumber.value.trim())) return { section: 'validationMessageBasic', message: 'ID number (JMBG) must be exactly 13 digits.' };

        if (dateOfBirth && dateOfBirth.value.trim()) {
            var parts = dateOfBirth.value.trim().split('.');
            if (parts.length !== 3) return { section: 'validationMessageBasic', message: 'Invalid date of birth (use dd.mm.yyyy).' };

            var d = parseInt(parts[0], 10);
            var m = parseInt(parts[1], 10) - 1;
            var y = parseInt(parts[2], 10);

            if (isNaN(d) || isNaN(m) || isNaN(y)) return { section: 'validationMessageBasic', message: 'Invalid date of birth.' };

            var birth = new Date(y, m, d);
            if (birth.getFullYear() !== y || birth.getMonth() !== m || birth.getDate() !== d) return { section: 'validationMessageBasic', message: 'Invalid date of birth.' };

            var today = new Date();
            today.setHours(0, 0, 0, 0);
            birth.setHours(0, 0, 0, 0);

            if (birth > today) return { section: 'validationMessageBasic', message: 'Date of birth cannot be in the future.' };

            var age = Math.floor((today - birth) / (365.25 * 24 * 60 * 60 * 1000));
            if (age < 16) return { section: 'validationMessageBasic', message: 'You must be at least 16 years old.' };
        }

        var genderChecked = formPart1 && formPart1.querySelector('input[name="gender"]:checked');
        if (!genderChecked) return { section: 'validationMessageAbout', message: 'Please select your gender.' };

        if (hasAccommodationYes && hasAccommodationYes.checked) {
            var accommodationAddress = document.getElementById('accommodationAddress');
            var accommodationType = formPart1.querySelector('input[name="accommodation_type"]:checked');
            var accommodationRent = document.getElementById('accommodationRent');

            if (!accommodationAddress || !accommodationAddress.value.trim()) return { section: 'validationMessageAbout', message: 'Your accommodation address is required.' };
            if (!accommodationType) return { section: 'validationMessageAbout', message: 'Please select accommodation type (house or apartment).' };
            if (!accommodationRent || !accommodationRent.value.trim() || parseFloat(accommodationRent.value) < 1) {
                return { section: 'validationMessageAbout', message: 'Monthly rent for roommate (EUR) is required and must be at least 1.' };
            }
        }

        if (hasPetYes && hasPetYes.checked) {
            var petType = document.getElementById('petType');
            if (!petType || !petType.value.trim()) return { section: 'validationMessageAbout', message: 'Please enter what pet you have.' };
        }

        if (hasPartiesYes && hasPartiesYes.checked) {
            var partyFrequency = document.getElementById('partyFrequency');
            if (!partyFrequency || !partyFrequency.value.trim()) return { section: 'validationMessageAbout', message: 'Please select how often you have parties.' };
        }

        if (playsInstrumentYes && playsInstrumentYes.checked) {
            var instrumentName = document.getElementById('instrumentName');
            if (!instrumentName || !instrumentName.value.trim()) return { section: 'validationMessageAbout', message: 'Please enter which instrument you play.' };
        }

        if (!hasAccommodationYes || !hasAccommodationYes.checked) {
            var preferredTypeChecked = formPart1 && formPart1.querySelector('input[name="preferred_type"]:checked');
            if (!preferredTypeChecked) return { section: 'validationMessageAccommodation', message: 'Please select preferred accommodation type.' };
        }

        return null;
    }

    function validatePart1Format() {
        var firstName = document.getElementById('firstName');
        var lastName = document.getElementById('lastName');
        var occupation = document.getElementById('occupation');
        var city = document.getElementById('city');
        var phone = document.getElementById('phone');
        var idNumber = document.getElementById('idNumber');

        function hasNoDigits(val) {
            if (!val || !val.trim()) return true;
            return !/\d/.test(val.trim());
        }

        if (firstName && !hasNoDigits(firstName.value)) return false;
        if (lastName && !hasNoDigits(lastName.value)) return false;
        if (occupation && occupation.value.trim() && !hasNoDigits(occupation.value)) return false;
        if (city && !hasNoDigits(city.value)) return false;

        if (phone && phone.value.trim()) {
            if (!/^\+38\d{9,10}$/.test(phone.value.trim())) return false;
        }

        if (idNumber && idNumber.value.trim()) {
            if (!/^\d{13}$/.test(idNumber.value.trim())) return false;
        }

        return true;
    }

    if (btnNext && formPart1 && formPart2) {
        btnNext.addEventListener('click', function () {
            function proceed() {
                var err = validatePart1WithSection();
                if (err) {
                    showSectionError(err.section, err.message);
                    return;
                }
                hideAllSectionErrors();
                formPart1.classList.add('form-part-hidden');
                formPart2.classList.remove('form-part-hidden');
                if (typeof onAccommodationChange === 'function') onAccommodationChange();
                window.scrollTo(0, 0);
            }

            var cityEl = document.getElementById('city');
            var cityLatEl = document.getElementById('cityLat');
            var cityLonEl = document.getElementById('cityLon');
            var preferredLocationInputEl = document.getElementById('preferredLocation');
            var preferredHasCoords = preferredLocationInputEl &&
                preferredLocationInputEl.value.trim() &&
                /^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$/.test(preferredLocationInputEl.value.trim());

            if (accommodationPreferencesSection && !accommodationPreferencesSection.hidden &&
                cityEl && cityEl.value.trim() &&
                cityLatEl && cityLonEl &&
                !preferredHasCoords) {
                btnNext.disabled = true;
                btnNext.textContent = 'Looking up city…';

                geocodeCityThenProceed(cityEl.value.trim(), function (coords) {
                    btnNext.disabled = false;
                    btnNext.textContent = 'Next';

                    if (coords) {
                        cityLatEl.value = coords.lat;
                        cityLonEl.value = coords.lon;
                    }
                    proceed();
                });
            } else {
                proceed();
            }
        });
    }

    if (btnBack && formPart1 && formPart2) {
        btnBack.addEventListener('click', function () {
            hideAllSectionErrors();
            formPart2.classList.add('form-part-hidden');
            formPart1.classList.remove('form-part-hidden');
            window.scrollTo(0, 0);
        });
    }

    // ----- Roommate preferences: conditional blocks -----
    var roommateAccommodationYes = document.getElementById('roommateAccommodationYes');
    var roommateAccommodationNo = document.getElementById('roommateAccommodationNo');
    var roommateAccommodationTypeBlock = document.getElementById('roommateAccommodationTypeBlock');

    var roommatePetOkYes = document.getElementById('roommatePetOkYes');
    var roommatePetOkNo = document.getElementById('roommatePetOkNo');
    var roommatePetsNotWantedBlock = document.getElementById('roommatePetsNotWantedBlock');

    var roommatePartiesOkYes = document.getElementById('roommatePartiesOkYes');
    var roommatePartiesOkNo = document.getElementById('roommatePartiesOkNo');
    var roommatePartyFrequencyBlock = document.getElementById('roommatePartyFrequencyBlock');

    var roommateInstrumentOkYes = document.getElementById('roommateInstrumentOkYes');
    var roommateInstrumentOkNo = document.getElementById('roommateInstrumentOkNo');
    var roommateInstrumentsBotherBlock = document.getElementById('roommateInstrumentsBotherBlock');

    function onRoommateAccommodationChange() {
        toggleBlock(roommateAccommodationYes && roommateAccommodationYes.checked, roommateAccommodationTypeBlock);
    }

    function onRoommatePetOkChange() {
        toggleBlock(roommatePetOkNo && roommatePetOkNo.checked, roommatePetsNotWantedBlock);
    }

    function onRoommatePartiesOkChange() {
        toggleBlock(roommatePartiesOkYes && roommatePartiesOkYes.checked, roommatePartyFrequencyBlock);
    }

    function onRoommateInstrumentOkChange() {
        toggleBlock(roommateInstrumentOkNo && roommateInstrumentOkNo.checked, roommateInstrumentsBotherBlock);
    }

    if (roommateAccommodationYes) roommateAccommodationYes.addEventListener('change', onRoommateAccommodationChange);
    if (roommateAccommodationNo) roommateAccommodationNo.addEventListener('change', onRoommateAccommodationChange);
    if (roommatePetOkYes) roommatePetOkYes.addEventListener('change', onRoommatePetOkChange);
    if (roommatePetOkNo) roommatePetOkNo.addEventListener('change', onRoommatePetOkChange);
    if (roommatePartiesOkYes) roommatePartiesOkYes.addEventListener('change', onRoommatePartiesOkChange);
    if (roommatePartiesOkNo) roommatePartiesOkNo.addEventListener('change', onRoommatePartiesOkChange);
    if (roommateInstrumentOkYes) roommateInstrumentOkYes.addEventListener('change', onRoommateInstrumentOkChange);
    if (roommateInstrumentOkNo) roommateInstrumentOkNo.addEventListener('change', onRoommateInstrumentOkChange);

    onAccommodationChange();
    onPetChange();
    onPartiesChange();
    onInstrumentChange();

    if (hasAccommodationYes) hasAccommodationYes.addEventListener('change', updateBudgetRequired);
    if (hasAccommodationNo) hasAccommodationNo.addEventListener('change', updateBudgetRequired);
    updateBudgetRequired();

    onRoommateAccommodationChange();
    onRoommatePetOkChange();
    onRoommatePartiesOkChange();
    onRoommateInstrumentOkChange();

    window.zimmerInitAccommodationMap = function (force) {
        if (!accommodationMapEl) return;
        if (!window.accommodationMapInstance) {
            initAccommodationMap(!!force);
        } else {
            scheduleAccommodationMapInitOrRefresh();
        }
    };
})();
