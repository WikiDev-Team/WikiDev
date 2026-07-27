function updateFriendPermission(select, customVisibility) {
    const row = select.closest("[data-friend-permission-row]");

    if (!row) {
        return;
    }

    const viewInput = row.querySelector(
        'input[name="shared_user_ids"]'
    );

    const editInput = row.querySelector(
        'input[name="editor_user_ids"]'
    );

    const permission = select.value;

    select.disabled = !customVisibility;

    if (viewInput) {
        viewInput.disabled =
            !customVisibility ||
            (permission !== "view" && permission !== "edit");
    }

    if (editInput) {
        editInput.disabled =
            !customVisibility ||
            permission !== "edit";
    }
}

function updatePageSharingForm(form) {
    const visibilitySelect = form.querySelector(
        "[data-page-visibility]"
    );

    const sharingFieldset = form.querySelector(
        "[data-page-sharing]"
    );

    if (!visibilitySelect || !sharingFieldset) {
        return;
    }

    const customVisibility =
        visibilitySelect.value === "custom";

    sharingFieldset.hidden = !customVisibility;
    sharingFieldset.disabled = !customVisibility;

    sharingFieldset
        .querySelectorAll("[data-friend-permission]")
        .forEach((select) => {
            updateFriendPermission(
                select,
                customVisibility
            );
        });
}

function initializePageSharing(root = document) {
    const forms = [];

    if (
        root instanceof Element &&
        root.matches("[data-page-sharing-form]")
    ) {
        forms.push(root);
    }

    root
        .querySelectorAll?.("[data-page-sharing-form]")
        .forEach((form) => {
            forms.push(form);
        });

    forms.forEach((form) => {
        if (form.dataset.pageSharingInitialized === "true") {
            updatePageSharingForm(form);
            return;
        }

        form.dataset.pageSharingInitialized = "true";

        const visibilitySelect = form.querySelector(
            "[data-page-visibility]"
        );

        visibilitySelect?.addEventListener("change", () => {
            updatePageSharingForm(form);
        });

        form
            .querySelectorAll("[data-friend-permission]")
            .forEach((select) => {
                select.addEventListener("change", () => {
                    updatePageSharingForm(form);
                });
            });

        updatePageSharingForm(form);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initializePageSharing();
});

document.body.addEventListener("htmx:afterSwap", (event) => {
    initializePageSharing(event.target);
});