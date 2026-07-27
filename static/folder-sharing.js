function syncFolderSharingForm(form) {
    const visibilitySelect = form.querySelector(
        "[data-folder-visibility]"
    );

    const sharingFieldset = form.querySelector(
        "[data-folder-sharing]"
    );

    if (!visibilitySelect || !sharingFieldset) {
        return;
    }

    const isCustom =
        visibilitySelect.value === "custom";

    sharingFieldset.hidden = !isCustom;
    sharingFieldset.disabled = !isCustom;
}

function initializeFolderSharing(root = document) {
    const forms = [];

    if (
        root instanceof Element &&
        root.matches("[data-folder-sharing-form]")
    ) {
        forms.push(root);
    }

    root
        .querySelectorAll?.("[data-folder-sharing-form]")
        .forEach((form) => {
            forms.push(form);
        });

    forms.forEach((form) => {
        if (
            form.dataset.folderSharingInitialized
            === "true"
        ) {
            syncFolderSharingForm(form);
            return;
        }

        form.dataset.folderSharingInitialized =
            "true";

        const visibilitySelect = form.querySelector(
            "[data-folder-visibility]"
        );

        visibilitySelect?.addEventListener(
            "change",
            () => {
                syncFolderSharingForm(form);
            }
        );

        syncFolderSharingForm(form);
    });
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeFolderSharing();
    }
);

document.body.addEventListener(
    "htmx:afterSwap",
    (event) => {
        initializeFolderSharing(event.target);
    }
);