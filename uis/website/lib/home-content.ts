export type SupportedLanguage = "en" | "es";

export interface TranslationDictionary {
  skipLink: string;
  brandTagline: string;
  navPrimary: string;
  languageSelector: string;
  themeLight: string;
  themeDark: string;
  themeSwitchToLight: string;
  themeSwitchToDark: string;
  navHome: string;
  navLocations: string;
  navMenu: string;
  navBrasaPoints: string;
  navContact: string;
  navOpenMenu: string;
  navCloseMenu: string;
  heroEyebrow: string;
  heroTitle: string;
  heroSubtitle: string;
  heroCta: string;
  heroSecondaryCta: string;
  storyEyebrow: string;
  storyTitle: string;
  storyBody: string;
  storyYears: string;
  storyLocations: string;
  uniqueEyebrow: string;
  uniqueTitle: string;
  uniqueSummary: string;
  qualityTitle: string;
  qualityPoint1: string;
  qualityPoint2: string;
  experienceTitle: string;
  experiencePoint1: string;
  experiencePoint2: string;
  speedTitle: string;
  speedPoint1: string;
  speedPoint2: string;
  locationsEyebrow: string;
  locationsTitle: string;
  locationsSummary: string;
  locationsColombiaCount: string;
  locationsUsaCount: string;
  colombiaTitle: string;
  colombiaPoint1: string;
  usaTitle: string;
  usaPoint1: string;
  hoursLabel: string;
  menuEyebrow: string;
  menuTitle: string;
  menuBody: string;
  menuValue1: string;
  menuValue2: string;
  menuValue3: string;
  menuValue4: string;
  menuCta: string;
  menuTeaserLine: string;
  menuBackToHome: string;
  pointsEyebrow: string;
  pointsTitle: string;
  pointsSubtitle: string;
  pointsItem1: string;
  pointsItem2: string;
  pointsItem3: string;
  pointsItem4: string;
  pointsCta: string;
  contactEyebrow: string;
  contactTitle: string;
  contactEmailLabel: string;
  contactColombiaLabel: string;
  contactFloridaLabel: string;
  orderNotice: string;
  footerCopyright: string;
  footerTagline: string;
  socialNav: string;
}

export const translations: Record<SupportedLanguage, TranslationDictionary> = {
  en: {
    skipLink: "Skip to main content",
    brandTagline: "Since 2008",
    navPrimary: "Primary navigation",
    languageSelector: "Language selector",
    themeLight: "Light",
    themeDark: "Dark",
    themeSwitchToLight: "Switch to light mode",
    themeSwitchToDark: "Switch to dark mode",
    navHome: "Home",
    navLocations: "Locations",
    navMenu: "Menu",
    navBrasaPoints: "Brasa Points",
    navContact: "Contact",
    navOpenMenu: "Open navigation menu",
    navCloseMenu: "Close navigation menu",
    heroEyebrow: "Brasaland Digital",
    heroTitle: "The taste of the grill, in every bite",
    heroSubtitle:
      "Since 2008 serving the best grilled meats in Colombia and the United States. 14 locations, one passion for quality and flavor.",
    heroCta: "Join Brasa Points",
    heroSecondaryCta: "Explore Locations",
    storyEyebrow: "Medellin, Colombia · 2008",
    storyTitle: "Our Story",
    storyBody:
      "Founded in Medellin in 2008, Brasaland began as a family dream: sharing the authentic taste of grilled meat with consistent quality and warm service. Today we are 14 restaurants in two countries, but we maintain the same recipe for success: fresh products, traditional techniques, and passion for every dish we serve.",
    storyYears: "years around the fire",
    storyLocations: "restaurants, one tradition",
    uniqueEyebrow: "The Brasaland standard",
    uniqueTitle: "What Makes Us Unique",
    uniqueSummary: "Tradition in the kitchen, consistency at every table.",
    qualityTitle: "Consistent Quality",
    qualityPoint1: "Same recipes and standards in all locations",
    qualityPoint2: "Fresh ingredients selected daily",
    experienceTitle: "Warm Experience",
    experiencePoint1: "Friendly and attentive service",
    experiencePoint2: "Family atmosphere on every visit",
    speedTitle: "Speed",
    speedPoint1: "Your food ready in minutes",
    speedPoint2: "Without sacrificing flavor or quality",
    locationsEyebrow: "Two countries · one table",
    locationsTitle: "Our Locations",
    locationsSummary:
      "Browse all 14 Brasaland restaurants across Colombia and the United States.",
    locationsColombiaCount: "7 restaurants in Colombia",
    locationsUsaCount: "7 restaurants in the United States",
    colombiaTitle: "Colombia",
    colombiaPoint1: "10 restaurants in Medellin, Bogota and Cali",
    usaTitle: "United States (Florida)",
    usaPoint1: "4 restaurants in Miami and Orlando",
    hoursLabel: "Hours: Mon-Sun 11:00 AM - 10:00 PM",
    menuEyebrow: "From the parrilla",
    menuTitle: "Menu Highlights",
    menuBody:
      "Signature grilled cuts, house marinades, and classic Colombian sides prepared with the same standard in every Brasaland restaurant.",
    menuValue1: "Fire",
    menuValue2: "Tradition",
    menuValue3: "Fresh",
    menuValue4: "Together",
    menuCta: "View full menu",
    menuTeaserLine: "9 categories · grill, seafood, bowls & more",
    menuBackToHome: "Back to home",
    pointsEyebrow: "Loyalty, served fresh",
    pointsTitle: "Brasa Points",
    pointsSubtitle: "Earn points with every visit",
    pointsItem1: "Accumulate 1 point for every $10,000 COP or $5 USD",
    pointsItem2: "Redeem your points for discounts and free dishes",
    pointsItem3: "Exclusive offers for members",
    pointsItem4: "100% digital registration - no more paper cards!",
    pointsCta: "Join Brasa Points",
    contactEyebrow: "Come say hello",
    contactTitle: "Contact",
    contactEmailLabel: "Email:",
    contactColombiaLabel: "Colombia:",
    contactFloridaLabel: "Florida:",
    orderNotice:
      "Want to place an order? Call your favorite location or visit us directly. Online ordering coming soon!",
    footerCopyright: "© 2025 Brasaland. All rights reserved.",
    footerTagline: "Medellin to Florida, always around the fire.",
    socialNav: "Social media",
  },
  es: {
    skipLink: "Saltar al contenido principal",
    brandTagline: "Desde 2008",
    navPrimary: "Navegacion principal",
    languageSelector: "Selector de idioma",
    themeLight: "Claro",
    themeDark: "Oscuro",
    themeSwitchToLight: "Cambiar al modo claro",
    themeSwitchToDark: "Cambiar al modo oscuro",
    navHome: "Inicio",
    navLocations: "Ubicaciones",
    navMenu: "Menu",
    navBrasaPoints: "Brasa Points",
    navContact: "Contacto",
    navOpenMenu: "Abrir menu de navegacion",
    navCloseMenu: "Cerrar menu de navegacion",
    heroEyebrow: "Brasaland Digital",
    heroTitle: "El sabor de la parrilla, en cada bocado",
    heroSubtitle:
      "Desde 2008 sirviendo las mejores carnes a la parrilla en Colombia y Estados Unidos. 14 sedes, una sola pasion por la calidad y el sabor.",
    heroCta: "Unete a Brasa Points",
    heroSecondaryCta: "Explorar ubicaciones",
    storyEyebrow: "Medellin, Colombia · 2008",
    storyTitle: "Nuestra Historia",
    storyBody:
      "Fundada en Medellin en 2008, Brasaland nacio como un sueno familiar: compartir el sabor autentico de la carne a la parrilla con calidad constante y un servicio calido. Hoy somos 14 restaurantes en dos paises, pero mantenemos la misma receta de exito: productos frescos, tecnicas tradicionales y pasion en cada plato.",
    storyYears: "anos alrededor del fuego",
    storyLocations: "restaurantes, una tradicion",
    uniqueEyebrow: "El estandar Brasaland",
    uniqueTitle: "Que Nos Hace Unicos",
    uniqueSummary: "Tradicion en la cocina, consistencia en cada mesa.",
    qualityTitle: "Calidad Constante",
    qualityPoint1: "Mismas recetas y estandares en todas las sedes",
    qualityPoint2: "Ingredientes frescos seleccionados a diario",
    experienceTitle: "Experiencia Calida",
    experiencePoint1: "Servicio amable y atento",
    experiencePoint2: "Ambiente familiar en cada visita",
    speedTitle: "Rapidez",
    speedPoint1: "Tu comida lista en minutos",
    speedPoint2: "Sin sacrificar sabor ni calidad",
    locationsEyebrow: "Dos paises · una mesa",
    locationsTitle: "Nuestras Ubicaciones",
    locationsSummary:
      "Explora las 14 sedes de Brasaland en Colombia y Estados Unidos.",
    locationsColombiaCount: "7 restaurantes en Colombia",
    locationsUsaCount: "7 restaurantes en Estados Unidos",
    colombiaTitle: "Colombia",
    colombiaPoint1: "10 restaurantes en Medellin, Bogota y Cali",
    usaTitle: "Estados Unidos (Florida)",
    usaPoint1: "4 restaurantes en Miami y Orlando",
    hoursLabel: "Horario: Lun-Dom 11:00 AM - 10:00 PM",
    menuEyebrow: "Desde la parrilla",
    menuTitle: "Destacados del Menu",
    menuBody:
      "Cortes a la parrilla, marinados de la casa y acompanamientos clasicos colombianos con el mismo estandar en cada restaurante Brasaland.",
    menuValue1: "Fuego",
    menuValue2: "Tradicion",
    menuValue3: "Frescura",
    menuValue4: "Juntos",
    menuCta: "Ver menu completo",
    menuTeaserLine: "9 categorias · parrilla, mar, bowls y mas",
    menuBackToHome: "Volver al inicio",
    pointsEyebrow: "Lealtad, siempre fresca",
    pointsTitle: "Brasa Points",
    pointsSubtitle: "Gana puntos en cada visita",
    pointsItem1: "Acumula 1 punto por cada $10,000 COP o $5 USD",
    pointsItem2: "Canjea tus puntos por descuentos y platos gratis",
    pointsItem3: "Ofertas exclusivas para miembros",
    pointsItem4: "Registro 100% digital - sin tarjetas de papel",
    pointsCta: "Unete a Brasa Points",
    contactEyebrow: "Ven a saludarnos",
    contactTitle: "Contacto",
    contactEmailLabel: "Correo:",
    contactColombiaLabel: "Colombia:",
    contactFloridaLabel: "Florida:",
    orderNotice:
      "Quieres hacer un pedido? Llama a tu sede favorita o visitanos directamente. Pedidos en linea proximamente.",
    footerCopyright: "© 2025 Brasaland. Todos los derechos reservados.",
    footerTagline: "De Medellin a Florida, siempre alrededor del fuego.",
    socialNav: "Redes sociales",
  },
};
