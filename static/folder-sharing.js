function updateFolderFriendPermission(select, customVisibility, customEditPolicy) {
    const row = select.closest("[data-folder-permission-row]");
    if (!row) return;

    const viewInput = row.querySelector('input[name="shared_user_ids"]');
    const editInput = row.querySelector('input[name="editor_user_ids"]');
    const permission = select.value;

    select.disabled = !customVisibility && !customEditPolicy;
    viewInput.disabled = !customVisibility || (permission !== "view" && permission !== "edit");
    editInput.disabled = !customEditPolicy || permission !== "edit";
}

function syncFolderSharingForm(form) {
    const visibilitySelect = form.querySelector("[data-folder-visibility]");
    const editPolicySelect = form.querySelector("[data-folder-edit-policy]");
    const sharingFieldset = form.querySelector("[data-folder-sharing]");

    if (!visibilitySelect || !editPolicySelect || !sharingFieldset) return;

    const customVisibility = visibilitySelect.value === "custom";
    const isPrivate = visibilitySelect.value === "private";
    const customEditPolicy = editPolicySelect.value === "custom";

    if (isPrivate) editPolicySelect.value = "owner";
    editPolicySelect.disabled = isPrivate;
    sharingFieldset.hidden = !customVisibility && !customEditPolicy;
    sharingFieldset.disabled = !customVisibility && !customEditPolicy;

    sharingFieldset.querySelectorAll("[data-folder-permission]").forEach((select) => {
        updateFolderFriendPermission(select, customVisibility, customEditPolicy);
    });
}

function initializeFolderSharing(root = document) {
    const forms = [];
    if (root instanceof Element && root.matches("[data-folder-sharing-form]")) forms.push(root);
    root.querySelectorAll?.("[data-folder-sharing-form]").forEach((form) => forms.push(form));

    forms.forEach((form) => {
        if (form.dataset.folderSharingInitialized === "true") {
            syncFolderSharingForm(form);
            return;
        }
        form.dataset.folderSharingInitialized = "true";
        const visibilitySelect = form.querySelector("[data-folder-visibility]");
        const editPolicySelect = form.querySelector("[data-folder-edit-policy]");
        visibilitySelect?.addEventListener("change", () => syncFolderSharingForm(form));
        editPolicySelect?.addEventListener("change", () => syncFolderSharingForm(form));
        form.querySelectorAll("[data-folder-permission]").forEach((select) => {
            select.addEventListener("change", () => {
                if (select.value === "edit" && visibilitySelect?.value === "custom" && editPolicySelect) {
                    editPolicySelect.value = "custom";
                }
                syncFolderSharingForm(form);
            });
        });
        syncFolderSharingForm(form);
    });
}

document.addEventListener("DOMContentLoaded", () => initializeFolderSharing());
document.body.addEventListener("htmx:afterSwap", (event) => initializeFolderSharing(event.target));
