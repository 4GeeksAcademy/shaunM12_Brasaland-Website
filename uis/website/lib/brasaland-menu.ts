import type { SupportedLanguage } from "@/lib/home-content";

export interface MenuItem {
  name: string;
  description: string;
  usd: string;
  cop: string;
}

export interface MenuSectionData {
  id: string;
  title: string;
  items: MenuItem[];
}

export interface MenuHero {
  eyebrow: string;
  title: string;
  description: string;
  badges: string[];
}

export interface MenuLocaleContent {
  hero: MenuHero;
  sections: MenuSectionData[];
}

export const brasalandMenu: Record<SupportedLanguage, MenuLocaleContent> = {
  es: {
    hero: {
      eyebrow: "Menu mockup para una marca con presencia en dos paises",
      title: "Brasaland",
      description:
        "Una propuesta de menu para Brasaland basada en el inventario sembrado: carnes a la parrilla, sabores colombianos, mariscos costenos, acompanamientos caseros y bebidas tropicales para Colombia y Florida.",
      badges: [
        "Colombia en COP",
        "Florida en USD",
        "Referencia FX: 1 USD = 3,366.9 COP",
      ],
    },
    sections: [
      {
        id: "entradas",
        title: "Entradas",
        items: [
          { name: "Yuca Frita con Alioli", description: "Yuca crocante con alioli de ajo y aji picante.", usd: "$7", cop: "COP 24,000" },
          { name: "Patacones con Hogao y Guacamole", description: "Platano verde crocante con hogao, guacamole y cilantro.", usd: "$8", cop: "COP 27,000" },
          { name: "Chicharron Crocante", description: "Panceta de cerdo crocante con salsa criolla y limon.", usd: "$12", cop: "COP 40,000" },
          { name: "Calamares al Ajillo", description: "Aros de calamar salteados en mantequilla de ajo.", usd: "$14", cop: "COP 47,000" },
          { name: "Ceviche de Camaron", description: "Camaron en leche de tigre con cebolla, tomate, cilantro y limon.", usd: "$15", cop: "COP 51,000" },
          { name: "Chorizo a la Parrilla", description: "Chorizo dorado servido con aji y arepita de maiz.", usd: "$10", cop: "COP 34,000" },
          { name: "Morcilla con Limon", description: "Morcilla asada con cebolla, cilantro y limon fresco.", usd: "$10", cop: "COP 34,000" },
        ],
      },
      {
        id: "parrilla-brasaland",
        title: "Parrilla Brasaland",
        items: [
          { name: "Brisket de la Casa", description: "Brisket cocido lentamente con chimichurri y salsa BBQ de la casa.", usd: "$19", cop: "COP 64,000" },
          { name: "Costillas BBQ", description: "Costillas de cerdo glaseadas con mostaza BBQ y yuca frita.", usd: "$21", cop: "COP 71,000" },
          { name: "Baby Back Ribs Ahumadas", description: "Costillas baby back con glaseado BBQ y salsa criolla.", usd: "$23", cop: "COP 77,000" },
          { name: "Pollo a la Brasa", description: "Muslo de pollo deshuesado en marinada de ajo y cilantro.", usd: "$17", cop: "COP 57,000" },
          { name: "Picanha a la Parrilla", description: "Punta de anca a la parrilla con salsa criolla.", usd: "$24", cop: "COP 81,000" },
          { name: "Entrana Marinada", description: "Entrana con chimichurri, limon y cebollin.", usd: "$23", cop: "COP 77,000" },
          { name: "Short Rib Braseado", description: "Short rib glaseado con BBQ de la casa y papas criollas estilo Brasaland.", usd: "$26", cop: "COP 88,000" },
          { name: "Parrillada Mixta", description: "Chorizo, morcilla, pollo y chicharron con arepa y aji.", usd: "$28", cop: "COP 94,000" },
        ],
      },
      {
        id: "especiales-del-chef",
        title: "Especiales del Chef",
        items: [
          { name: "Lomo Fino a la Parrilla", description: "Medallones de res con chimichurri y papas de la casa.", usd: "$29", cop: "COP 98,000" },
          { name: "Cordero Braseado", description: "Cordero lentamente cocido con mojo criollo y cebolla asada.", usd: "$27", cop: "COP 91,000" },
          { name: "Pavo a la Parrilla", description: "Muslo de pavo marinado con ajo, limon y cilantro.", usd: "$18", cop: "COP 61,000" },
          { name: "Pechuga de Pato Sellada", description: "Pato a la plancha con salsa criolla y platano maduro.", usd: "$28", cop: "COP 94,000" },
        ],
      },
      {
        id: "del-mar",
        title: "Del Mar",
        items: [
          { name: "Pargo Rojo a la Plancha", description: "Pargo rojo con mojo verde y platano maduro.", usd: "$26", cop: "COP 88,000" },
          { name: "Mahi-Mahi al Mojo", description: "Mahi-mahi al mojo citrico con tomate y cebolla salteada.", usd: "$22", cop: "COP 74,000" },
          { name: "Tilapia Criolla", description: "Tilapia sellada terminada con hogao y cilantro.", usd: "$18", cop: "COP 61,000" },
          { name: "Camarones al Ajillo", description: "Camaron salteado en mantequilla de ajo, limon y cebollin.", usd: "$20", cop: "COP 67,000" },
          { name: "Ceviche Mixto de la Costa", description: "Pescado para ceviche en leche de tigre con jalapeno, cilantro y limon.", usd: "$17", cop: "COP 57,000" },
          { name: "Vieiras y Almejas al Sarten", description: "Vieiras y almejas en salsa de ajo y cilantro.", usd: "$24", cop: "COP 81,000" },
          { name: "Parrillada de Mariscos", description: "Camaron, vieiras, almejas y mezcla de mariscos con mojo verde.", usd: "$30", cop: "COP 101,000" },
        ],
      },
      {
        id: "mar-premium",
        title: "Mar Premium",
        items: [
          { name: "Salmon a la Plancha", description: "Salmon sellado con mojo verde y aguacate fresco.", usd: "$24", cop: "COP 81,000" },
          { name: "Cherna al Hogao", description: "Filete de cherna con hogao, cilantro y limon.", usd: "$27", cop: "COP 91,000" },
          { name: "Atun Sellado", description: "Lomo de atun a la plancha con salsa verde y cebollin.", usd: "$25", cop: "COP 84,000" },
          { name: "Langostinos al Ajillo", description: "Langostinos salteados en mantequilla de ajo y limon.", usd: "$29", cop: "COP 98,000" },
          { name: "Caracol de Mar en Salsa Criolla", description: "Caracol picado con tomate, cebolla, cilantro y limon.", usd: "$23", cop: "COP 77,000" },
        ],
      },
      {
        id: "arepas-y-bowls",
        title: "Arepas y Bowls",
        items: [
          { name: "Arepa con Carne Molida", description: "Arepa a la plancha con carne molida sazonada, hogao y aguacate.", usd: "$14", cop: "COP 47,000" },
          { name: "Arepa de Chorizo", description: "Chorizo, salsa criolla y crema chipotle.", usd: "$13", cop: "COP 44,000" },
          { name: "Arepa de Pollo y Aguacate", description: "Pollo a la brasa, aguacate y alioli de ajo.", usd: "$14", cop: "COP 47,000" },
          { name: "Bowl de Pollo y Frijoles", description: "Pollo a la parrilla, frijol negro, aguacate, tomate y platano.", usd: "$16", cop: "COP 54,000" },
          { name: "Bowl Costeno de Camaron", description: "Camaron, aguacate, tomate, cilantro y crocante de patacon.", usd: "$18", cop: "COP 61,000" },
          { name: "Bowl de Picanha", description: "Picanha, papas de la casa, cebolla, tomate y salsa criolla.", usd: "$20", cop: "COP 67,000" },
        ],
      },
      {
        id: "acompanamientos",
        title: "Acompanamientos",
        items: [
          { name: "Arepa de Maiz", description: "Arepa de la casa.", usd: "$4", cop: "COP 13,000" },
          { name: "Yuca Frita", description: "Yuca crocante.", usd: "$5", cop: "COP 17,000" },
          { name: "Patacones", description: "Tostones de platano verde.", usd: "$6", cop: "COP 20,000" },
          { name: "Platano Maduro", description: "Platano dulce caramelizado.", usd: "$6", cop: "COP 20,000" },
          { name: "Papas de la Casa", description: "Papas sazonadas al estilo Brasaland.", usd: "$6", cop: "COP 20,000" },
          { name: "Frijoles Negros", description: "Frijol negro guisado.", usd: "$5", cop: "COP 17,000" },
          { name: "Aguacate Fresco", description: "Aguacate fresco con limon y sal.", usd: "$5", cop: "COP 17,000" },
        ],
      },
      {
        id: "bebidas",
        title: "Bebidas",
        items: [
          { name: "Limonada de Coco", description: "Refrescante de coco y limon.", usd: "$6", cop: "COP 20,000" },
          { name: "Jugo de Maracuya", description: "Jugo tropical de maracuya.", usd: "$5", cop: "COP 17,000" },
          { name: "Mango Agua Fresca", description: "Bebida fresca de mango.", usd: "$5", cop: "COP 17,000" },
          { name: "Aguapanela", description: "Bebida tradicional de panela.", usd: "$4", cop: "COP 13,000" },
          { name: "Horchata", description: "Bebida de arroz y canela.", usd: "$5", cop: "COP 17,000" },
          { name: "Te Helado con Limon", description: "Te helado estilo casa con limon.", usd: "$4", cop: "COP 13,000" },
          { name: "Cafe Colombiano", description: "Cafe filtrado de la casa.", usd: "$4", cop: "COP 13,000" },
        ],
      },
      {
        id: "salsas-de-la-casa",
        title: "Salsas de la Casa",
        items: [
          { name: "Chimichurri", description: "Salsa fresca de hierbas para carnes a la parrilla.", usd: "$2", cop: "COP 7,000" },
          { name: "Aji de la Casa", description: "Salsa picante colombiana con cilantro y limon.", usd: "$2", cop: "COP 7,000" },
          { name: "Salsa BBQ Brasaland", description: "BBQ dulce y ahumada de la casa.", usd: "$2", cop: "COP 7,000" },
          { name: "Mojo Verde", description: "Salsa de cilantro y limon para pescados y mariscos.", usd: "$2", cop: "COP 7,000" },
          { name: "Tartara", description: "Salsa cremosa para pescados apanados o a la plancha.", usd: "$2", cop: "COP 7,000" },
          { name: "Dip de Camaron Coco", description: "Dip cremoso y tropical para mariscos y entradas.", usd: "$3", cop: "COP 10,000" },
        ],
      },
    ],
  },
  en: {
    hero: {
      eyebrow: "Menu mockup for a two-country brand",
      title: "Brasaland",
      description:
        "A Brasaland menu concept built from the seeded inventory: grilled meats, Colombian comfort flavors, coastal seafood, house sides, and tropical drinks designed to read naturally for both Colombia and Florida.",
      badges: [
        "Florida pricing in USD",
        "Colombia pricing in COP",
        "FX reference: 1 USD = 3,366.9 COP",
      ],
    },
    sections: [
      {
        id: "starters",
        title: "Starters",
        items: [
          { name: "Yuca Fries with Garlic Aioli", description: "Crispy cassava fries with garlic aioli and house hot sauce.", usd: "$7", cop: "COP 24,000" },
          { name: "Patacones with Hogao and Guacamole", description: "Crispy green plantains topped with hogao, guacamole, and cilantro.", usd: "$8", cop: "COP 27,000" },
          { name: "Crispy Pork Belly Bites", description: "Crackling pork belly with onion-lime salsa and fresh lime.", usd: "$12", cop: "COP 40,000" },
          { name: "Garlic Calamari", description: "Squid rings sauteed in seafood garlic butter.", usd: "$14", cop: "COP 47,000" },
          { name: "Shrimp Ceviche", description: "Shrimp in leche de tigre with onion, tomato, cilantro, and lime.", usd: "$15", cop: "COP 51,000" },
          { name: "Grilled Chorizo", description: "Charred chorizo with aji sauce and a mini corn arepa.", usd: "$10", cop: "COP 34,000" },
          { name: "Morcilla with Lime", description: "Grilled blood sausage with fresh herbs and lime.", usd: "$10", cop: "COP 34,000" },
        ],
      },
      {
        id: "from-the-grill",
        title: "From the Grill",
        items: [
          { name: "House Brisket", description: "Slow-cooked beef brisket with chimichurri and house BBQ sauce.", usd: "$19", cop: "COP 64,000" },
          { name: "BBQ Pork Ribs", description: "Pork ribs glazed with mustard BBQ and served with yuca fries.", usd: "$21", cop: "COP 71,000" },
          { name: "Smoked Baby Back Ribs", description: "Baby back ribs with smoky BBQ glaze and onion-lime salsa.", usd: "$23", cop: "COP 77,000" },
          { name: "Chicken a la Brasa", description: "Boneless chicken thigh in a garlic-cilantro marinade.", usd: "$17", cop: "COP 57,000" },
          { name: "Grilled Picanha", description: "Top sirloin cap grilled and finished with onion-lime salsa.", usd: "$24", cop: "COP 81,000" },
          { name: "Marinated Skirt Steak", description: "Skirt steak with chimichurri, lime, and scallions.", usd: "$23", cop: "COP 77,000" },
          { name: "Braised Short Rib", description: "Rich short rib glazed with house BBQ and Brasaland potatoes.", usd: "$26", cop: "COP 88,000" },
          { name: "Mixed Grill Platter", description: "Chorizo, morcilla, chicken, and pork belly with arepa and aji.", usd: "$28", cop: "COP 94,000" },
        ],
      },
      {
        id: "chef-specials",
        title: "Chef Specials",
        items: [
          { name: "Grilled Beef Tenderloin", description: "Beef tenderloin medallions with chimichurri and house potatoes.", usd: "$29", cop: "COP 98,000" },
          { name: "Braised Lamb Shoulder", description: "Slow-cooked lamb shoulder with mojo criollo and grilled onion.", usd: "$27", cop: "COP 91,000" },
          { name: "Grilled Turkey Thigh", description: "Marinated turkey thigh with garlic, lime, and cilantro.", usd: "$18", cop: "COP 61,000" },
          { name: "Seared Duck Breast", description: "Pan-seared duck breast with salsa criolla and sweet plantain.", usd: "$28", cop: "COP 94,000" },
        ],
      },
      {
        id: "coastal-seafood",
        title: "Coastal Seafood",
        items: [
          { name: "Griddled Red Snapper", description: "Red snapper with mojo verde and sweet plantain.", usd: "$26", cop: "COP 88,000" },
          { name: "Mahi-Mahi al Mojo", description: "Citrus-garlic mahi-mahi with sauteed tomato and onion.", usd: "$22", cop: "COP 74,000" },
          { name: "Tilapia Criolla", description: "Seared tilapia finished with hogao and cilantro.", usd: "$18", cop: "COP 61,000" },
          { name: "Garlic Shrimp", description: "Shrimp sauteed in garlic butter with lime and scallions.", usd: "$20", cop: "COP 67,000" },
          { name: "Coastal Mixed Ceviche", description: "Ceviche fish blend in leche de tigre with jalapeno, cilantro, and lime.", usd: "$17", cop: "COP 57,000" },
          { name: "Scallops and Clams Skillet", description: "Sea scallops and clams in a bright garlic-cilantro sauce.", usd: "$24", cop: "COP 81,000" },
          { name: "Seafood Grill", description: "Shrimp, scallops, clams, and mixed seafood with mojo verde.", usd: "$30", cop: "COP 101,000" },
        ],
      },
      {
        id: "premium-seafood",
        title: "Premium Seafood",
        items: [
          { name: "Griddled Salmon", description: "Seared salmon with mojo verde and fresh avocado.", usd: "$24", cop: "COP 81,000" },
          { name: "Grouper with Hogao", description: "Grouper fillet topped with hogao, cilantro, and lime.", usd: "$27", cop: "COP 91,000" },
          { name: "Seared Tuna Steak", description: "Tuna steak with salsa verde and scallions.", usd: "$25", cop: "COP 84,000" },
          { name: "Garlic Langoustines", description: "Langoustines sauteed in garlic butter and lime.", usd: "$29", cop: "COP 98,000" },
          { name: "Conch in Criolla Sauce", description: "Diced conch with tomato, onion, cilantro, and lime.", usd: "$23", cop: "COP 77,000" },
        ],
      },
      {
        id: "arepas-and-bowls",
        title: "Arepas and Bowls",
        items: [
          { name: "Beef Arepa", description: "Griddled arepa stuffed with seasoned ground beef, hogao, and avocado.", usd: "$14", cop: "COP 47,000" },
          { name: "Chorizo Arepa", description: "Chorizo, onion-lime salsa, and chipotle crema.", usd: "$13", cop: "COP 44,000" },
          { name: "Chicken and Avocado Arepa", description: "Grilled chicken, avocado, and garlic aioli.", usd: "$14", cop: "COP 47,000" },
          { name: "Chicken and Bean Bowl", description: "Grilled chicken, black beans, avocado, tomato, and plantain.", usd: "$16", cop: "COP 54,000" },
          { name: "Coastal Shrimp Bowl", description: "Shrimp, avocado, tomato, cilantro, and patacon crunch.", usd: "$18", cop: "COP 61,000" },
          { name: "Picanha Bowl", description: "Picanha, house potatoes, onion, tomato, and salsa criolla.", usd: "$20", cop: "COP 67,000" },
        ],
      },
      {
        id: "sides",
        title: "Sides",
        items: [
          { name: "House Corn Arepa", description: "Warm house corn arepa.", usd: "$4", cop: "COP 13,000" },
          { name: "Yuca Fries", description: "Crispy cassava fries.", usd: "$5", cop: "COP 17,000" },
          { name: "Patacones", description: "Crisp green plantain rounds.", usd: "$6", cop: "COP 20,000" },
          { name: "Sweet Plantain", description: "Caramelized ripe plantain.", usd: "$6", cop: "COP 20,000" },
          { name: "Brasaland Potatoes", description: "Seasoned potato wedges.", usd: "$6", cop: "COP 20,000" },
          { name: "Black Beans", description: "Slow-stewed black beans.", usd: "$5", cop: "COP 17,000" },
          { name: "Fresh Avocado", description: "Sliced avocado with lime and salt.", usd: "$5", cop: "COP 17,000" },
        ],
      },
      {
        id: "drinks",
        title: "Drinks",
        items: [
          { name: "Coconut Limeade", description: "A creamy coconut and lime refresher.", usd: "$6", cop: "COP 20,000" },
          { name: "Passion Fruit Juice", description: "Tropical passion fruit cooler.", usd: "$5", cop: "COP 17,000" },
          { name: "Mango Agua Fresca", description: "Fresh mango cooler.", usd: "$5", cop: "COP 17,000" },
          { name: "Aguapanela", description: "Traditional panela drink.", usd: "$4", cop: "COP 13,000" },
          { name: "Horchata", description: "Rice-and-cinnamon house refresher.", usd: "$5", cop: "COP 17,000" },
          { name: "Lime Sweet Tea", description: "House iced tea with lime.", usd: "$4", cop: "COP 13,000" },
          { name: "Colombian Coffee", description: "Fresh brewed Colombian coffee.", usd: "$4", cop: "COP 13,000" },
        ],
      },
      {
        id: "house-sauces",
        title: "House Sauces",
        items: [
          { name: "Chimichurri", description: "Fresh herb sauce for grilled meats.", usd: "$2", cop: "COP 7,000" },
          { name: "House Aji", description: "Colombian-style hot sauce with cilantro and lime.", usd: "$2", cop: "COP 7,000" },
          { name: "Brasaland BBQ", description: "Sweet smoky house barbecue sauce.", usd: "$2", cop: "COP 7,000" },
          { name: "Mojo Verde", description: "Cilantro-lime sauce for fish and seafood.", usd: "$2", cop: "COP 7,000" },
          { name: "Tartar Sauce", description: "Creamy tartar sauce for grilled or crispy seafood.", usd: "$2", cop: "COP 7,000" },
          { name: "Coconut Shrimp Dip", description: "Creamy tropical dip for seafood and starters.", usd: "$3", cop: "COP 10,000" },
        ],
      },
    ],
  },
};

export function getMenuPrice(item: MenuItem, language: SupportedLanguage): string {
  return language === "en" ? item.usd : item.cop;
}
