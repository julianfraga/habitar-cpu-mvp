(() => {
  const activeForms = new WeakSet();

  function showToast(message, level = "error") {
    let region = document.getElementById("toast-region");
    if (!region) {
      region = document.createElement("div");
      region.id = "toast-region";
      region.className = "fixed top-4 right-4 z-50 flex flex-col gap-3 p-4 pointer-events-none";
      region.setAttribute("aria-live", "polite");
      document.body.append(region);
    }

    const toast = document.createElement("div");
    toast.dataset.toast = "";
    toast.setAttribute("role", level === "error" ? "alert" : "status");
    toast.className = `pointer-events-auto flex items-start gap-3 radius-panel elevation-floating border-width px-4 py-3 type-body-small ${
      level === "error"
        ? "surface-danger-soft border-danger text-danger-contrast"
        : level === "info"
          ? "surface-info border-info text-info"
          : "surface-success-soft border-success text-success-contrast"
    }`;

    const text = document.createElement("span");
    text.textContent = message;
    const dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.dataset.toastDismiss = "";
    dismiss.setAttribute("aria-label", "Cerrar notificación");
    dismiss.className = "ml-auto weight-bold";
    dismiss.textContent = "×";
    toast.append(text, dismiss);
    region.append(toast);
    scheduleToastDismiss(toast);
  }

  window.showToast = showToast;

  function scheduleToastDismiss(toast) {
    window.setTimeout(() => toast.remove(), 6000);
  }

  function bindToastDismiss(region = document) {
    region.querySelectorAll("[data-toast]").forEach(scheduleToastDismiss);
  }

  async function activatePageScripts(container) {
    const scripts = Array.from(container.querySelectorAll("script"));
    for (const oldScript of scripts) {
      const scriptType = oldScript.type;
      if (scriptType && scriptType !== "text/javascript" && scriptType !== "application/javascript") {
        continue;
      }

      if (oldScript.src) {
        await new Promise((resolve) => {
          const activeScript = document.createElement("script");
          activeScript.src = oldScript.src;
          activeScript.async = false;
          activeScript.onload = resolve;
          activeScript.onerror = () => {
            console.error("No se pudo cargar script de página:", oldScript.src);
            resolve();
          };
          oldScript.replaceWith(activeScript);
        });
      } else {
        try {
          new Function(oldScript.textContent)();
        } catch (error) {
          console.error("No se pudo inicializar script de página:", error);
        }
        oldScript.remove();
      }
    }
  }

  async function updatePageFromResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      if (payload.message) showToast(payload.message, response.ok ? "success" : "error");
      else if (!response.ok) showToast("No se pudo completar la acción.");
      return;
    }

    const html = await response.text();
    const nextDocument = new DOMParser().parseFromString(html, "text/html");
    const nextMain = nextDocument.querySelector("main");
    const currentMain = document.querySelector("main");
    if (!nextMain || !currentMain) {
      showToast("El servidor devolvió una respuesta inesperada.");
      return;
    }

    currentMain.replaceWith(nextMain);
    document.title = nextDocument.title;

    const currentHeader = document.querySelector("body > header");
    const nextHeader = nextDocument.querySelector("body > header");
    if (currentHeader && nextHeader) currentHeader.replaceWith(nextHeader);
    else if (currentHeader) currentHeader.remove();
    else if (nextHeader) document.body.prepend(nextHeader);

    const currentToasts = document.getElementById("toast-region");
    const nextToasts = nextDocument.getElementById("toast-region");
    if (currentToasts && nextToasts) currentToasts.replaceWith(nextToasts);
    else if (!currentToasts && nextToasts) document.body.prepend(nextToasts);

    const currentFooter = document.querySelector("body > footer");
    const nextFooter = nextDocument.querySelector("body > footer");
    if (currentFooter && nextFooter) currentFooter.replaceWith(nextFooter);
    else if (currentFooter) currentFooter.remove();
    else if (nextFooter) document.body.append(nextFooter);

    const currentScripts = document.getElementById("page-scripts");
    const nextScripts = nextDocument.getElementById("page-scripts");
    if (currentScripts && nextScripts) {
      currentScripts.replaceWith(nextScripts);
      await activatePageScripts(nextScripts);
    }

    const nextUrl = new URL(response.url, window.location.href);
    nextUrl.searchParams.delete("msg");
    nextUrl.searchParams.delete("err");
    nextUrl.searchParams.delete("notice");
    window.history.replaceState(null, "", `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
    bindToastDismiss(document);
    if (window.lucide) window.lucide.createIcons();
    if (!response.ok && !document.querySelector("#toast-region [data-toast]")) {
      const errorText = nextMain.querySelector('[role="alert"]')?.textContent.trim();
      showToast(errorText || "No se pudo completar la acción.");
    }
  }

  document.addEventListener("click", (event) => {
    const dismiss = event.target instanceof Element
      ? event.target.closest("[data-toast-dismiss]")
      : null;
    if (dismiss) dismiss.closest("[data-toast]")?.remove();

    const navToggle = event.target instanceof Element
      ? event.target.closest("#nav-toggle")
      : null;
    const siteNavigation = navToggle && document.getElementById("site-navigation");
    if (navToggle && siteNavigation) {
      const isExpanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!isExpanded));
      navToggle.setAttribute("aria-label", isExpanded ? "Abrir menú" : "Cerrar menú");
      siteNavigation.classList.toggle("hidden", isExpanded);
      siteNavigation.classList.toggle("flex", !isExpanded);
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (
      !(form instanceof HTMLFormElement) ||
      form.method.toUpperCase() !== "POST" ||
      form.dataset.nativeSubmit === "true" ||
      form.target ||
      event.defaultPrevented ||
      activeForms.has(form)
    ) {
      return;
    }

    event.preventDefault();
    activeForms.add(form);
    form.setAttribute("aria-busy", "true");
    const submitter = event.submitter;
    if (submitter instanceof HTMLButtonElement || submitter instanceof HTMLInputElement) {
      submitter.disabled = true;
    }

    try {
      const body = submitter
        ? new FormData(form, submitter)
        : new FormData(form);
      const response = await fetch(form.action || window.location.href, {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: {
          Accept: "text/html, application/json",
          "X-Requested-With": "fetch",
        },
      });
      await updatePageFromResponse(response);
    } catch (error) {
      console.error("No se pudo completar acción del formulario:", error);
      showToast("No se pudo conectar con el servidor. Intentá nuevamente.");
    } finally {
      activeForms.delete(form);
      form.removeAttribute("aria-busy");
      if (submitter instanceof HTMLButtonElement || submitter instanceof HTMLInputElement) {
        submitter.disabled = false;
      }
    }
  });

  bindToastDismiss();
})();
