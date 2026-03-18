/**
 * My profile page: view/edit toggle, AJAX submit for edit form, delete confirmation modal.
 * Author: Jovana Ceganjac 2022/0423
 */
(function () {
    'use strict';

    var profileViewBlock = document.getElementById('profileViewBlock');
    var profileEditBlock = document.getElementById('profileEditBlock');
    var btnShowEditProfile = document.getElementById('btnShowEditProfile');
    var btnCancelEdit = document.getElementById('btnCancelEdit');
    var pageTitleEl = document.getElementById('profilePageTitle');
    var pageSubtitleEl = document.getElementById('profilePageSubtitle');

    function refreshLeafletMap(mapInstance) {
        if (!mapInstance || typeof mapInstance.invalidateSize !== 'function') return;

        try {
            var center = typeof mapInstance.getCenter === 'function' ? mapInstance.getCenter() : null;
            var zoom = typeof mapInstance.getZoom === 'function' ? mapInstance.getZoom() : null;

            mapInstance.invalidateSize();

            if (center && typeof zoom === 'number') {
                mapInstance.setView(center, zoom, { animate: false });
            }

            setTimeout(function () {
                try {
                    mapInstance.invalidateSize();
                    if (center && typeof zoom === 'number') {
                        mapInstance.setView(center, zoom, { animate: false });
                    }
                } catch (e) {}
            }, 150);

            setTimeout(function () {
                try {
                    mapInstance.invalidateSize();
                } catch (e) {}
            }, 400);
        } catch (e) {}
    }

    function initAndRefreshMaps() {
        if (typeof window.zimmerInitAccommodationMap === 'function') {
            try {
                window.zimmerInitAccommodationMap(true);
            } catch (e) {}
        }

        if (typeof window.zimmerInitPreferredMap === 'function') {
            try {
                window.zimmerInitPreferredMap(true);
            } catch (e) {}
        }

        requestAnimationFrame(function () {
            refreshLeafletMap(window.accommodationMapInstance);
            refreshLeafletMap(window.preferredMapInstance);

            setTimeout(function () {
                refreshLeafletMap(window.accommodationMapInstance);
                refreshLeafletMap(window.preferredMapInstance);
            }, 200);
        });
    }

    function showView() {
        if (profileViewBlock) profileViewBlock.style.display = '';
        if (profileEditBlock) {
            profileEditBlock.hidden = true;
            profileEditBlock.style.display = '';
        }
        if (pageTitleEl) pageTitleEl.textContent = 'My Profile';
        if (pageSubtitleEl) pageSubtitleEl.textContent = 'Your profile at a glance';
        window.scrollTo(0, 0);
    }

    function showEdit() {
        if (profileViewBlock) profileViewBlock.style.display = 'none';
        if (profileEditBlock) {
            profileEditBlock.hidden = false;
            profileEditBlock.style.display = '';
        }
        if (pageTitleEl) pageTitleEl.textContent = 'Edit my profile';
        if (pageSubtitleEl) pageSubtitleEl.textContent = 'Update your details';
        window.scrollTo(0, 0);

        initAndRefreshMaps();
    }

    if (btnShowEditProfile) {
        btnShowEditProfile.addEventListener('click', showEdit);
    }
    if (btnCancelEdit) {
        btnCancelEdit.addEventListener('click', showView);
    }

    var deleteProfileForm = document.getElementById('deleteProfileForm');
    var deleteModal = document.getElementById('deleteProfileModal');
    var deleteModalCancel = document.getElementById('deleteProfileModalCancel');
    var deleteModalConfirm = document.getElementById('deleteProfileModalConfirm');

    if (deleteProfileForm && deleteModal) {
        deleteProfileForm.addEventListener('submit', function (e) {
            e.preventDefault();
            deleteModal.hidden = false;
            document.body.style.overflow = 'hidden';
        });

        function closeDeleteModal() {
            deleteModal.hidden = true;
            document.body.style.overflow = '';
        }

        if (deleteModalCancel) {
            deleteModalCancel.addEventListener('click', closeDeleteModal);
        }
        if (deleteModalConfirm) {
            deleteModalConfirm.addEventListener('click', function () {
                closeDeleteModal();
                deleteProfileForm.submit();
            });
        }
        deleteModal.addEventListener('click', function (e) {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }

    // AJAX submit for profile edit
    var profileEditForm = document.getElementById('profileEditForm');
    var profileEditFormMessage = document.getElementById('profileEditFormMessage');
    var submitBtn = profileEditForm ? profileEditForm.querySelector('button[type="submit"]') : null;

    function getCsrfToken() {
        var match = document.cookie.match(/\bcsrftoken=([^;]+)/);
        return match ? match[1].trim() : '';
    }

    function showFormMessage(text, isError) {
        if (!profileEditFormMessage) return;
        profileEditFormMessage.textContent = text;
        profileEditFormMessage.hidden = false;
        profileEditFormMessage.classList.toggle('validation-message--error', isError !== false);
        profileEditFormMessage.classList.toggle('validation-message--success', isError === false);
    }

    function hideSectionValidationMessages() {
        ['validationMessageBasic', 'validationMessageAbout', 'validationMessageAccommodation', 'validationMessageRoommate'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) {
                el.hidden = true;
                el.textContent = '';
            }
        });
        if (profileEditFormMessage) {
            profileEditFormMessage.hidden = true;
            profileEditFormMessage.textContent = '';
        }
    }

    if (profileEditForm) {
        profileEditForm.addEventListener('submit', function (e) {
            e.preventDefault();

            var form = this;
            var formData = new FormData(form);

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.setAttribute('aria-busy', 'true');
            }
            hideSectionValidationMessages();

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            }).then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) {
                        throw new Error(data.error || 'A technical error occurred. Please try again.');
                    }
                    return data;
                }, function () {
                    if (!response.ok) {
                        throw new Error('A technical error occurred. Please try again.');
                    }
                    throw new Error('Invalid response from server.');
                });
            }).then(function (data) {
                if (data.ok && data.redirect_url) {
                    showFormMessage('Profile saved! Redirecting…', false);
                    window.setTimeout(function () {
                        window.location.href = data.redirect_url;
                    }, 800);
                } else {
                    var sectionId = data.error_section || 'profileEditFormMessage';
                    var msg = data.error || 'Please correct the errors below.';
                    if (sectionId === 'profileEditFormMessage') {
                        showFormMessage(msg, true);
                    } else {
                        var sectionEl = document.getElementById(sectionId);
                        if (sectionEl) {
                            sectionEl.textContent = msg;
                            sectionEl.hidden = false;
                            sectionEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        } else {
                            showFormMessage(msg, true);
                        }
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.removeAttribute('aria-busy');
                    }
                }
            }).catch(function (err) {
                showFormMessage(err.message || 'A technical error occurred. Please try again.', true);
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.removeAttribute('aria-busy');
                }
            });
        });
    }
})();
