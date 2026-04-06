const form = document.getElementById("applicationForm");
const messageBox = document.getElementById("formMessage");
const countrySelect = document.getElementById("country");
const citySelect = document.getElementById("city");
const favoriteLocationSelect = document.getElementById("favoriteLocation");
const clearFormButton = document.getElementById("clearFormButton");
const languageButtons = document.querySelectorAll("[data-lang-switch]");

const languageStorageKey = "brasaland_lang";

const countries = [
  { value: "colombia", label: { en: "Colombia", es: "Colombia" } },
  { value: "united-states", label: { en: "United States", es: "Estados Unidos" } }
];

const citiesByCountry = {
  colombia: [
    { value: "medellin", label: { en: "Medellin", es: "Medellín" } },
    { value: "bogota", label: { en: "Bogota", es: "Bogotá" } },
    { value: "cali", label: { en: "Cali", es: "Cali" } }
  ],
  "united-states": [
    { value: "miami", label: { en: "Miami", es: "Miami" } },
    { value: "orlando", label: { en: "Orlando", es: "Orlando" } }
  ]
};

const locationsByCountryCity = {
  "colombia|medellin": ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
  "colombia|bogota": ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  "colombia|cali": ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  "united-states|miami": ["Brasaland Brickell", "Brasaland Coral Gables"],
  "united-states|orlando": ["Brasaland Downtown", "Brasaland International Drive"]
};

const translations = {
  en: {
    languageSelector: "Language selector",
    formTitle: "Join Brasa Points",
    formSubtitle:
      "Complete the form to create your digital loyalty profile and start earning points at any Brasaland location.",
    orderNotice:
      "Want to place an order? Call your favorite location or visit us directly. Online ordering coming soon!",
    fullNameLabel: "Full name",
    fullNamePlaceholder: "Jane Doe",
    emailLabel: "Email",
    emailPlaceholder: "name@email.com",
    phoneLabel: "Phone",
    countryLabel: "Country",
    countryPlaceholder: "Select your country",
    cityLabel: "City",
    cityPlaceholder: "Select your city",
    favoriteLocationLabel: "Favorite Brasaland location",
    favoriteLocationPlaceholder: "Select location (optional)",
    favoriteLocationHelp: "Options update based on country and city.",
    discoveryLabel: "How did you find us?",
    discoveryPlaceholder: "Tell us how you found Brasaland",
    discoverySocial: "Social media",
    discoveryRecommendation: "Recommendation",
    discoveryWalkedBy: "Walked by",
    discoveryInternetSearch: "Internet search",
    discoveryOther: "Other",
    dobLabel: "Date of birth",
    dietaryLegend: "Dietary preferences",
    dietaryHelp: "Select all that apply.",
    dietaryNone: "No restrictions",
    dietaryVegetarian: "Vegetarian",
    dietaryGlutenFree: "Gluten-free",
    dietaryOther: "Other",
    consentLegend: "Consent",
    acceptTermsLabel: "I accept program terms",
    emailOffersLabel: "I want to receive offers via email",
    submitButton: "Submit registration",
    clearButton: "Clear form",
    backButton: "Back to home",
    errorFullName: "Enter your full name (first and last name)",
    errorEmail: "Enter a valid email (example: <name@email.com>)",
    errorPhone:
      "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)",
    errorCountry: "Select your country",
    errorCity: "Select your city",
    errorDiscovery: "Tell us how you found Brasaland",
    errorDob: "You must be 18 or older to register for Brasa Points",
    errorTerms: "You must accept the Brasa Points program terms to continue",
    successTitle: "Welcome to Brasa Points!",
    successBody:
      "Your registration was successful. You will receive a confirmation email in the next few minutes with your account details and how to start earning points. You can now enjoy your benefits at any of our 14 locations!"
  },
  es: {
    languageSelector: "Selector de idioma",
    formTitle: "Únete a Brasa Points",
    formSubtitle:
      "Completa el formulario para crear tu perfil digital de fidelización y comenzar a ganar puntos en cualquier sede de Brasaland.",
    orderNotice:
      "¿Quieres hacer un pedido? Llama a tu sede favorita o visítanos directamente. Pedidos en línea próximamente.",
    fullNameLabel: "Nombre completo",
    fullNamePlaceholder: "Nombre y apellido",
    emailLabel: "Correo electrónico",
    emailPlaceholder: "nombre@correo.com",
    phoneLabel: "Teléfono",
    countryLabel: "País",
    countryPlaceholder: "Selecciona tu país",
    cityLabel: "Ciudad",
    cityPlaceholder: "Selecciona tu ciudad",
    favoriteLocationLabel: "Sede Brasaland favorita",
    favoriteLocationPlaceholder: "Selecciona sede (opcional)",
    favoriteLocationHelp: "Las opciones cambian según país y ciudad.",
    discoveryLabel: "¿Cómo nos conociste?",
    discoveryPlaceholder: "Cuéntanos cómo conociste Brasaland",
    discoverySocial: "Redes sociales",
    discoveryRecommendation: "Recomendación",
    discoveryWalkedBy: "Paso por el local",
    discoveryInternetSearch: "Búsqueda en internet",
    discoveryOther: "Otro",
    dobLabel: "Fecha de nacimiento",
    dietaryLegend: "Preferencias alimentarias",
    dietaryHelp: "Selecciona todas las que apliquen.",
    dietaryNone: "Sin restricciones",
    dietaryVegetarian: "Vegetariano",
    dietaryGlutenFree: "Sin gluten",
    dietaryOther: "Otro",
    consentLegend: "Consentimiento",
    acceptTermsLabel: "Acepto los términos del programa",
    emailOffersLabel: "Quiero recibir ofertas por correo",
    submitButton: "Enviar registro",
    clearButton: "Limpiar formulario",
    backButton: "Volver al inicio",
    errorFullName: "Ingresa tu nombre completo (nombre y apellido)",
    errorEmail: "Ingresa un correo válido (ejemplo: nombre@correo.com)",
    errorPhone: "El teléfono debe incluir código de país (ejemplo: +57 300 123 4567 o +1 305 123 4567)",
    errorCountry: "Selecciona tu país",
    errorCity: "Selecciona tu ciudad",
    errorDiscovery: "Cuéntanos cómo conociste Brasaland",
    errorDob: "Debes tener 18 años o más para registrarte en Brasa Points",
    errorTerms: "Debes aceptar los términos del programa Brasa Points para continuar",
    successTitle: "Bienvenido a Brasa Points!",
    successBody:
      "Tu registro fue exitoso. Recibirás un correo de confirmación en los próximos minutos con los detalles de tu cuenta y cómo empezar a acumular puntos. Ya puedes disfrutar tus beneficios en cualquiera de nuestras 14 sedes."
  }
};

const fieldErrorMap = {
  fullName: "fullNameError",
  email: "emailError",
  phone: "phoneError",
  country: "countryError",
  city: "cityError",
  discoverySource: "discoverySourceError",
  dateOfBirth: "dateOfBirthError",
  acceptTerms: "acceptTermsError"
};

function getCurrentLanguage() {
  const savedLanguage = localStorage.getItem(languageStorageKey);
  return translations[savedLanguage] ? savedLanguage : "en";
}

function translate(key) {
  const lang = getCurrentLanguage();
  return translations[lang][key] || translations.en[key] || "";
}

function setOptions(selectElement, options, placeholderText) {
  selectElement.innerHTML = "";

  const placeholderOption = document.createElement("option");
  placeholderOption.value = "";
  placeholderOption.textContent = placeholderText;
  selectElement.appendChild(placeholderOption);

  options.forEach((option) => {
    const optionElement = document.createElement("option");
    optionElement.value = option.value;
    optionElement.textContent = option.label;
    selectElement.appendChild(optionElement);
  });
}

function applyStaticTranslations() {
  const lang = getCurrentLanguage();
  const dictionary = translations[lang];

  document.documentElement.lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (dictionary[key]) {
      element.textContent = dictionary[key];
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.dataset.i18nPlaceholder;
    if (dictionary[key]) {
      element.setAttribute("placeholder", dictionary[key]);
    }
  });

  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    const key = element.dataset.i18nAriaLabel;
    if (dictionary[key]) {
      element.setAttribute("aria-label", dictionary[key]);
    }
  });

  languageButtons.forEach((button) => {
    const isActive = button.dataset.langSwitch === lang;
    button.classList.toggle("border-amber-300", isActive);
    button.classList.toggle("text-amber-300", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  setCountryOptions();
  setCityOptions();
  setFavoriteLocationOptions();
}

function setCountryOptions() {
  const selectedCountry = countrySelect.value;
  const lang = getCurrentLanguage();
  setOptions(
    countrySelect,
    countries.map((country) => ({ value: country.value, label: country.label[lang] })),
    translate("countryPlaceholder")
  );
  countrySelect.value = selectedCountry;
}

function setCityOptions() {
  const selectedCity = citySelect.value;
  const selectedCountry = countrySelect.value;
  const lang = getCurrentLanguage();
  const cityOptions = (citiesByCountry[selectedCountry] || []).map((city) => ({
    value: city.value,
    label: city.label[lang]
  }));

  setOptions(citySelect, cityOptions, translate("cityPlaceholder"));

  if (cityOptions.some((city) => city.value === selectedCity)) {
    citySelect.value = selectedCity;
  }
}

function setFavoriteLocationOptions() {
  const selectedLocation = favoriteLocationSelect.value;
  const key = `${countrySelect.value}|${citySelect.value}`;
  const locationOptions = (locationsByCountryCity[key] || []).map((location) => ({
    value: location,
    label: location
  }));

  setOptions(favoriteLocationSelect, locationOptions, translate("favoriteLocationPlaceholder"));

  if (locationOptions.some((location) => location.value === selectedLocation)) {
    favoriteLocationSelect.value = selectedLocation;
  }
}

function setFieldError(fieldName, message) {
  const errorElement = document.getElementById(fieldErrorMap[fieldName]);
  const fieldElement = form.elements[fieldName];

  if (!errorElement || !fieldElement) {
    return;
  }

  if (message) {
    errorElement.textContent = message;
    errorElement.classList.remove("hidden");
    fieldElement.classList.add("border-red-400", "focus:border-red-400", "focus:ring-red-300/20");
    fieldElement.setAttribute("aria-invalid", "true");
  } else {
    errorElement.textContent = "";
    errorElement.classList.add("hidden");
    fieldElement.classList.remove("border-red-400", "focus:border-red-400", "focus:ring-red-300/20");
    fieldElement.setAttribute("aria-invalid", "false");
  }
}

function isAdult(dateString) {
  if (!dateString) {
    return false;
  }

  const today = new Date();
  const birthDate = new Date(dateString + "T00:00:00");
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDifference = today.getMonth() - birthDate.getMonth();

  if (monthDifference < 0 || (monthDifference === 0 && today.getDate() < birthDate.getDate())) {
    age -= 1;
  }

  return age >= 18;
}

function validateField(fieldName) {
  const value = form.elements[fieldName]?.value?.trim() || "";

  switch (fieldName) {
    case "fullName": {
      const hasTwoWords = /^\S+\s+\S+/.test(value);
      const error = hasTwoWords ? "" : translate("errorFullName");
      setFieldError(fieldName, error);
      return !error;
    }
    case "email": {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const error = emailPattern.test(value) ? "" : translate("errorEmail");
      setFieldError(fieldName, error);
      return !error;
    }
    case "phone": {
      const phonePattern = /^\+(57|1)\s[0-9\s-]{7,}$/;
      const country = form.elements.country.value;
      const countryPrefixMatches =
        !country ||
        (country === "colombia" && value.startsWith("+57")) ||
        (country === "united-states" && value.startsWith("+1"));
      const isValid = phonePattern.test(value) && countryPrefixMatches;
      const error = isValid ? "" : translate("errorPhone");
      setFieldError(fieldName, error);
      return !error;
    }
    case "country": {
      const error = value ? "" : translate("errorCountry");
      setFieldError(fieldName, error);
      return !error;
    }
    case "city": {
      const error = value ? "" : translate("errorCity");
      setFieldError(fieldName, error);
      return !error;
    }
    case "discoverySource": {
      const error = value ? "" : translate("errorDiscovery");
      setFieldError(fieldName, error);
      return !error;
    }
    case "dateOfBirth": {
      const error = isAdult(value) ? "" : translate("errorDob");
      setFieldError(fieldName, error);
      return !error;
    }
    case "acceptTerms": {
      const accepted = form.elements.acceptTerms.checked;
      const error = accepted ? "" : translate("errorTerms");
      setFieldError(fieldName, error);
      return !error;
    }
    default:
      return true;
  }
}

function validateAllRequiredFields() {
  return [
    "fullName",
    "email",
    "phone",
    "country",
    "city",
    "discoverySource",
    "dateOfBirth",
    "acceptTerms"
  ].every((fieldName) => validateField(fieldName));
}

function clearFormMessage() {
  messageBox.className = "hidden rounded-xl border px-4 py-3 text-sm font-semibold sm:text-base";
  messageBox.innerHTML = "";
}

function showErrorSummary() {
  messageBox.className =
    "block rounded-xl border border-red-300 bg-red-100/10 px-4 py-3 text-sm font-semibold text-red-200 sm:text-base";
  messageBox.textContent = "Please correct the highlighted fields before submitting.";
}

function showSuccessMessage() {
  messageBox.className =
    "block rounded-xl border border-emerald-300 bg-emerald-100/10 px-4 py-3 text-sm font-semibold text-emerald-200 sm:text-base";
  messageBox.innerHTML = `<strong>${translate("successTitle")}</strong> ${translate("successBody")}`;
}

function clearAllErrors() {
  Object.keys(fieldErrorMap).forEach((fieldName) => setFieldError(fieldName, ""));
}

function resetDependentFields() {
  citySelect.value = "";
  favoriteLocationSelect.value = "";
  setCityOptions();
  setFavoriteLocationOptions();
}

if (form && messageBox && countrySelect && citySelect && favoriteLocationSelect && clearFormButton) {
  applyStaticTranslations();

  languageButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextLanguage = button.dataset.langSwitch;
      localStorage.setItem(languageStorageKey, nextLanguage);
      applyStaticTranslations();
      clearAllErrors();
      clearFormMessage();
    });
  });

  countrySelect.addEventListener("change", () => {
    resetDependentFields();
    validateField("country");
    validateField("city");
    validateField("phone");
  });

  citySelect.addEventListener("change", () => {
    favoriteLocationSelect.value = "";
    setFavoriteLocationOptions();
    validateField("city");
  });

  ["fullName", "email", "phone"].forEach((fieldName) => {
    form.elements[fieldName].addEventListener("input", () => validateField(fieldName));
    form.elements[fieldName].addEventListener("blur", () => validateField(fieldName));
  });

  ["discoverySource", "dateOfBirth", "acceptTerms"].forEach((fieldName) => {
    form.elements[fieldName].addEventListener("change", () => validateField(fieldName));
    form.elements[fieldName].addEventListener("blur", () => validateField(fieldName));
  });

  clearFormButton.addEventListener("click", () => {
    form.reset();
    clearAllErrors();
    clearFormMessage();
    setCountryOptions();
    resetDependentFields();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearFormMessage();

    const isValid = validateAllRequiredFields();
    if (!isValid) {
      showErrorSummary();
      return;
    }

    showSuccessMessage();
  });
}
