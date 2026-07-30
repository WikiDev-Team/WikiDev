function updateFriendPermission(select, customVisibility, customEditPolicy) {
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

    select.disabled = !customVisibility && !customEditPolicy;

    if (viewInput) {
        viewInput.disabled =
            !customVisibility ||
            (permission !== "view" && permission !== "edit");
    }

    if (editInput) {
        editInput.disabled =
            !customEditPolicy ||
            permission !== "edit";
    }
}

function updatePageSharingForm(form) {
    const visibilitySelect = form.querySelector(
        "[data-page-visibility]"
    );

    const editPolicySelect = form.querySelector(
        "[data-page-edit-policy]"
    );

    const sharingFieldset = form.querySelector(
        "[data-page-sharing]"
    );

    if (!visibilitySelect || !editPolicySelect || !sharingFieldset) {
        return;
    }

    const customVisibility =
        visibilitySelect.value === "custom";
    const isPrivate = visibilitySelect.value === "private";
    const customEditPolicy = editPolicySelect.value === "custom";

    if (isPrivate) {
        editPolicySelect.value = "owner";
    }
    editPolicySelect.disabled = isPrivate;
    sharingFieldset.hidden = !customVisibility && !customEditPolicy;
    sharingFieldset.disabled = !customVisibility && !customEditPolicy;

    sharingFieldset
        .querySelectorAll("[data-friend-permission]")
        .forEach((select) => {
            updateFriendPermission(
                select,
                customVisibility,
                customEditPolicy
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
        const editPolicySelect = form.querySelector(
            "[data-page-edit-policy]"
        );

        visibilitySelect?.addEventListener("change", () => {
            updatePageSharingForm(form);
        });

        editPolicySelect?.addEventListener("change", () => {
            updatePageSharingForm(form);
        });

        form
            .querySelectorAll("[data-friend-permission]")
            .forEach((select) => {
                select.addEventListener("change", () => {
                    if (
                        select.value === "edit" &&
                        visibilitySelect?.value === "custom" &&
                        editPolicySelect
                    ) {
                        editPolicySelect.value = "custom";
                    }
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
