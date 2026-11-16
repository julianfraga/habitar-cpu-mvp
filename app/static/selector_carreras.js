function initializeCareerSelector() {
  const select = document.getElementById("carrera-select");
  const tagsContainer = document.getElementById("carreras-tags-container");
  const hiddenInputsContainer = document.getElementById("carreras-hidden-inputs");
  const emptyMsg = document.getElementById("carreras-empty-msg");
  const allCareersValue = select?.dataset.allCareersValue;

  if (!select || !tagsContainer || !hiddenInputsContainer) return;
  if (select.dataset.careerSelectorInitialized === "true") return;
  select.dataset.careerSelectorInitialized = "true";

  const form = select.closest("form");
  const shouldAutoSubmit = form && form.dataset.autoSubmit === "true";
  const selectedValues = new Set();

  function triggerAutoSubmit() {
    if (shouldAutoSubmit && form) {
      form.submit();
    }
  }

  function updateEmptyMessage() {
    if (emptyMsg) {
      emptyMsg.style.display = selectedValues.size === 0 ? "block" : "none";
    }
  }

  function addTag(value, labelText, isInitializing = false) {
    if (selectedValues.has(value)) {
      select.value = "";
      return;
    }

    if (value === allCareersValue) {
      Array.from(selectedValues).forEach((v) => removeTag(v, isInitializing));
    } else if (selectedValues.has(allCareersValue)) {
      removeTag(allCareersValue, isInitializing);
    }

    selectedValues.add(value);

    // 1. Crear el elemento visual (Tag)
    const tag = document.createElement("span");
    tag.id = `tag-${value}`;
    tag.className =
      "inline-flex items-center gap-1.5 bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1.5 rounded-full cursor-pointer hover:bg-red-100 hover:text-red-800 transition-colors";

    tag.innerHTML = `
      <span>${labelText}</span>
      <svg class="w-3.5 h-3.5 opacity-70 hover:opacity-100" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
      </svg>
    `;

    tag.addEventListener("click", () => removeTag(value));
    tagsContainer.appendChild(tag);

    // 2. Crear el input oculto
    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = "carreras_asociadas";
    hiddenInput.value = value;
    hiddenInput.id = `input-${value}`;
    hiddenInputsContainer.appendChild(hiddenInput);

    updateEmptyMessage();
    select.value = "";

    // Si no estamos en la fase de precarga inicial, disparar el auto-submit
    if (!isInitializing) {
      triggerAutoSubmit();
    }
  }

  function removeTag(value, isInitializing = false) {
    selectedValues.delete(value);

    const tagElem = document.getElementById(`tag-${value}`);
    const inputElem = document.getElementById(`input-${value}`);

    if (tagElem) tagElem.remove();
    if (inputElem) inputElem.remove();

    updateEmptyMessage();

    if (!isInitializing) {
      triggerAutoSubmit();
    }
  }

  // Escuchar cambio en el select
  select.addEventListener("change", (e) => {
    const val = e.target.value;
    if (!val) return;

    const selectedOption = e.target.options[e.target.selectedIndex];
    const label =
      val === allCareersValue
        ? "TODAS LAS CARRERAS"
        : selectedOption.getAttribute("data-nombre") || selectedOption.text;

    addTag(val, label);
  });

  // Precargar elementos en modo EDICIÓN o con filtros aplicados (sin auto-submit)
  const preselected = document.querySelectorAll(".preselected-carrera");
  preselected.forEach((el) => {
    const id = el.getAttribute("data-id");
    const nombre = el.getAttribute("data-nombre");
    if (id && nombre) {
      addTag(id, nombre, true); // true indica que es inicialización
    }
  });
}

window.initializeCareerSelector = initializeCareerSelector;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeCareerSelector);
} else {
  initializeCareerSelector();
}

const careerSelectorObserver = new MutationObserver(initializeCareerSelector);
careerSelectorObserver.observe(document.body, { childList: true, subtree: true });