#!/usr/bin/env node

const readline = require("node:readline/promises");
const { stdin: input, stdout: output } = require("node:process");

const exchangeRate = 4000;

const menuItems = [
  {
    id: "ITEM-PICANHA-250",
    name: "Picanha 250g",
    category: "Meat",
    basePrice: { USD: 18.5, COP: 74000 },
    ingredientCost: { USD: 7.2, COP: 28800 },
    prepTimeMinutes: 15,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-FRIES",
    name: "French Fries",
    category: "Side",
    basePrice: { USD: 4.5, COP: 18000 },
    ingredientCost: { USD: 1.2, COP: 4800 },
    prepTimeMinutes: 8,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-COKE",
    name: "Coca-Cola",
    category: "Beverage",
    basePrice: { USD: 2.5, COP: 10000 },
    ingredientCost: { USD: 0.8, COP: 3200 },
    prepTimeMinutes: 2,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
];

const locations = [
  {
    id: "LOC-MEDELLIN-01",
    name: "Brasaland Medellin Centro",
    city: "Medellin",
    country: "Colombia",
    openingYear: 2008,
    seatingCapacity: 80,
    staffCount: 12,
    monthlyRentCost: { USD: 1500, COP: 6000000 },
    averageMonthlyUtilities: { USD: 400, COP: 1600000 },
    manager: "Carlos Jimenez",
    status: "Active",
  },
  {
    id: "LOC-MIAMI-01",
    name: "Brasaland Miami Beach",
    city: "Miami",
    country: "USA",
    openingYear: 2018,
    seatingCapacity: 100,
    staffCount: 15,
    monthlyRentCost: { USD: 5500, COP: 22000000 },
    averageMonthlyUtilities: { USD: 800, COP: 3200000 },
    manager: "Jake Morrison",
    status: "Active",
  },
];

const sales = [
  {
    id: "TXN-2024-15482",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 2,
    totalPrice: { USD: 37.0, COP: 148000 },
    paymentMethod: "Credit card",
    timestamp: new Date("2024-03-15T19:30:00Z"),
    waiterName: "Maria Gonzalez",
  },
  {
    id: "TXN-2024-15483",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-FRIES",
    quantity: 3,
    totalPrice: { USD: 13.5, COP: 54000 },
    paymentMethod: "Cash",
    timestamp: new Date("2024-03-15T20:15:00Z"),
    waiterName: "John Smith",
  },
  {
    id: "TXN-2024-15484",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-COKE",
    quantity: 4,
    totalPrice: { USD: 10.0, COP: 40000 },
    paymentMethod: "Digital wallet",
    timestamp: new Date("2024-03-16T12:40:00Z"),
    waiterName: "Sofia Rivera",
  },
];

const wasteRecords = [
  {
    id: "WST-01",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-FRIES",
    quantity: 2,
    reason: "Expired",
    cost: { USD: 2.4, COP: 9600 },
    timestamp: new Date("2024-03-15T21:00:00Z"),
    reportedBy: "Carlos",
  },
  {
    id: "WST-02",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 1,
    reason: "Cooking error",
    cost: { USD: 7.2, COP: 28800 },
    timestamp: new Date("2024-03-16T13:10:00Z"),
    reportedBy: "Jake",
  },
];

function round2(value) {
  return Number(value.toFixed(2));
}

function convertCurrency(amount, fromCurrency, toCurrency) {
  if (fromCurrency === toCurrency) return round2(amount);
  if (fromCurrency === "USD" && toCurrency === "COP") return round2(amount * exchangeRate);
  return round2(amount / exchangeRate);
}

function filterSalesByLocation(rows, locationId) {
  return rows.filter((sale) => sale.locationId === locationId);
}

function filterSalesByDateRange(rows, startDate, endDate) {
  return rows.filter((sale) => sale.timestamp >= startDate && sale.timestamp <= endDate);
}

function filterMenuItemsByCategory(items, category) {
  return items.filter((item) => item.category === category);
}

function filterActiveLocations(rows) {
  return rows.filter((loc) => loc.status === "Active");
}

function sortLocationsByCapacity(rows, order) {
  return [...rows].sort((a, b) =>
    order === "asc" ? a.seatingCapacity - b.seatingCapacity : b.seatingCapacity - a.seatingCapacity,
  );
}

function sortMenuItemsByPrice(items, currency, order) {
  return [...items].sort((a, b) =>
    order === "asc" ? a.basePrice[currency] - b.basePrice[currency] : b.basePrice[currency] - a.basePrice[currency],
  );
}

function findLocationById(rows, id) {
  return rows.find((loc) => loc.id === id) ?? null;
}

function findMenuItemByName(items, name) {
  const normalized = name.trim().toLowerCase();
  return items.find((item) => item.name.toLowerCase() === normalized) ?? null;
}

function binarySearchLocationByCapacity(sortedLocations, targetCapacity) {
  let left = 0;
  let right = sortedLocations.length - 1;
  while (left <= right) {
    const middle = Math.floor((left + right) / 2);
    const value = sortedLocations[middle].seatingCapacity;
    if (value === targetCapacity) return middle;
    if (value < targetCapacity) left = middle + 1;
    else right = middle - 1;
  }
  return -1;
}

function calculateDailyRevenue(rows, date, currency) {
  const targetDate = date.toISOString().slice(0, 10);
  const total = rows
    .filter((sale) => sale.timestamp.toISOString().slice(0, 10) === targetDate)
    .reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  return round2(total);
}

function calculateLocationMargin(rows, items, locationId, currency) {
  const scopedSales = rows.filter((sale) => sale.locationId === locationId);
  const revenue = scopedSales.reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  if (revenue === 0) return 0;

  const ingredientCost = scopedSales.reduce((sum, sale) => {
    const item = items.find((menuItem) => menuItem.id === sale.itemId);
    if (!item) return sum;
    return sum + item.ingredientCost[currency] * sale.quantity;
  }, 0);

  return round2(((revenue - ingredientCost) / revenue) * 100);
}

function calculateWasteCost(records, locationId, currency) {
  return round2(
    records
      .filter((record) => record.locationId === locationId)
      .reduce((sum, record) => sum + record.cost[currency], 0),
  );
}

function scoreLocationPerformance(location, allSales, allWaste, items) {
  const locationSales = allSales.filter((sale) => sale.locationId === location.id);
  const totalRevenueUSD = locationSales.reduce((sum, sale) => sum + sale.totalPrice.USD, 0);
  const operatingDays = Math.max(1, (new Date().getFullYear() - location.openingYear + 1) * 365);
  const avgDailyRevenue = totalRevenueUSD / operatingDays;
  const revenueScore = Math.min(40, (avgDailyRevenue / 1000) * 40);

  const efficiencyScore = Math.min(30, (locationSales.length / location.seatingCapacity) * 30);

  const wasteUSD = calculateWasteCost(allWaste, location.id, "USD");
  const wastePercentage = totalRevenueUSD > 0 ? (wasteUSD / totalRevenueUSD) * 100 : 100;
  const wasteControlScore = Math.max(0, 20 - wastePercentage * 2);

  const margin = calculateLocationMargin(allSales, items, location.id, "USD");
  const marginScore = Math.min(10, margin / 10);

  return round2(revenueScore + efficiencyScore + wasteControlScore + marginScore);
}

function rankLocationsByPerformance(allLocations, allSales, allWaste, items) {
  return allLocations
    .map((location) => ({
      location,
      score: scoreLocationPerformance(location, allSales, allWaste, items),
    }))
    .sort((a, b) => b.score - a.score);
}

function countSalesByPaymentMethod(rows) {
  const result = { Cash: 0, "Credit card": 0, "Debit card": 0, "Digital wallet": 0 };
  rows.forEach((sale) => {
    result[sale.paymentMethod] += 1;
  });
  return result;
}

function calculateAverageTicket(rows, currency) {
  if (rows.length === 0) return 0;
  const total = rows.reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  return round2(total / rows.length);
}

function findTopSellingItems(allSales, items, topN) {
  const soldByItem = {};
  allSales.forEach((sale) => {
    soldByItem[sale.itemId] = (soldByItem[sale.itemId] || 0) + sale.quantity;
  });

  return Object.entries(soldByItem)
    .map(([itemId, totalSold]) => ({ item: items.find((entry) => entry.id === itemId), totalSold }))
    .filter((entry) => entry.item)
    .sort((a, b) => b.totalSold - a.totalSold)
    .slice(0, topN);
}

function groupWasteByReason(records) {
  return records.reduce((grouped, record) => {
    if (!grouped[record.reason]) grouped[record.reason] = [];
    grouped[record.reason].push(record);
    return grouped;
  }, {});
}

function calculateCountryComparison(allSales, allLocations) {
  const mapCountry = {
    Colombia: {
      totalLocations: 0,
      totalRevenue: { USD: 0, COP: 0 },
      averageRevenuePerLocation: { USD: 0, COP: 0 },
      totalSales: 0,
    },
    USA: {
      totalLocations: 0,
      totalRevenue: { USD: 0, COP: 0 },
      averageRevenuePerLocation: { USD: 0, COP: 0 },
      totalSales: 0,
    },
  };

  allLocations.forEach((loc) => {
    mapCountry[loc.country].totalLocations += 1;
  });

  allSales.forEach((sale) => {
    const loc = allLocations.find((entry) => entry.id === sale.locationId);
    if (!loc) return;
    mapCountry[loc.country].totalRevenue.USD += sale.totalPrice.USD;
    mapCountry[loc.country].totalRevenue.COP += sale.totalPrice.COP;
    mapCountry[loc.country].totalSales += 1;
  });

  Object.keys(mapCountry).forEach((country) => {
    const metrics = mapCountry[country];
    metrics.averageRevenuePerLocation.USD = metrics.totalLocations
      ? round2(metrics.totalRevenue.USD / metrics.totalLocations)
      : 0;
    metrics.averageRevenuePerLocation.COP = metrics.totalLocations
      ? round2(metrics.totalRevenue.COP / metrics.totalLocations)
      : 0;
    metrics.totalRevenue.USD = round2(metrics.totalRevenue.USD);
    metrics.totalRevenue.COP = round2(metrics.totalRevenue.COP);
  });

  return mapCountry;
}

function validateMenuItem(item) {
  const errors = [];
  if (!item.name || !item.name.trim()) errors.push("name must not be empty");
  if (item.basePrice.USD <= 0 || item.basePrice.COP <= 0) errors.push("both base prices must be > 0");
  if (item.prepTimeMinutes <= 0 || item.prepTimeMinutes > 60)
    errors.push("prepTimeMinutes must be > 0 and <= 60");
  if (!item.isAvailableInColombia && !item.isAvailableInUSA)
    errors.push("item must be available in at least one country");
  return { valid: errors.length === 0, errors };
}

function validateSaleTransaction(sale) {
  const errors = [];
  if (sale.quantity <= 0) errors.push("quantity must be > 0");
  if (sale.totalPrice.USD <= 0 || sale.totalPrice.COP <= 0) errors.push("both price values must be > 0");
  if (!sale.waiterName || !sale.waiterName.trim()) errors.push("waiterName must not be empty");
  return { valid: errors.length === 0, errors };
}

function validateLocation(location) {
  const errors = [];
  const currentYear = new Date().getFullYear();
  if (location.openingYear < 2008 || location.openingYear > currentYear)
    errors.push("openingYear must be between 2008 and current year");
  if (location.seatingCapacity <= 0) errors.push("seatingCapacity must be > 0");
  if (location.staffCount <= 0) errors.push("staffCount must be > 0");
  if (location.monthlyRentCost.USD <= 0 || location.monthlyRentCost.COP <= 0)
    errors.push("rent costs must be > 0");
  if (location.averageMonthlyUtilities.USD <= 0 || location.averageMonthlyUtilities.COP <= 0)
    errors.push("utility costs must be > 0");
  return { valid: errors.length === 0, errors };
}

const functionNames = [
  "filterSalesByLocation",
  "filterSalesByDateRange",
  "filterMenuItemsByCategory",
  "filterActiveLocations",
  "sortLocationsByCapacity",
  "sortMenuItemsByPrice",
  "findLocationById",
  "findMenuItemByName",
  "binarySearchLocationByCapacity",
  "calculateDailyRevenue",
  "calculateLocationMargin",
  "calculateWasteCost",
  "convertCurrency",
  "scoreLocationPerformance",
  "rankLocationsByPerformance",
  "countSalesByPaymentMethod",
  "calculateAverageTicket",
  "findTopSellingItems",
  "groupWasteByReason",
  "calculateCountryComparison",
  "validateMenuItem",
  "validateSaleTransaction",
  "validateLocation",
];

function humanizeName(name) {
  return name
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^./, (char) => char.toUpperCase());
}

function formatPrimitive(value) {
  if (value instanceof Date) return value.toISOString();
  if (value === null || value === undefined) return "-";
  return String(value);
}

function printPretty(value, indent = 0) {
  const pad = " ".repeat(indent);

  if (Array.isArray(value)) {
    if (value.length === 0) {
      console.log(`${pad}[]`);
      return;
    }

    value.forEach((item, index) => {
      if (item && typeof item === "object") {
        console.log(`${pad}- [${index + 1}]`);
        printPretty(item, indent + 2);
      } else {
        console.log(`${pad}- ${formatPrimitive(item)}`);
      }
    });
    return;
  }

  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    if (entries.length === 0) {
      console.log(`${pad}{}`);
      return;
    }

    entries.forEach(([key, nested]) => {
      if (nested && typeof nested === "object") {
        console.log(`${pad}${humanizeName(key)}:`);
        printPretty(nested, indent + 2);
      } else {
        console.log(`${pad}${humanizeName(key)}: ${formatPrimitive(nested)}`);
      }
    });
    return;
  }

  console.log(`${pad}${formatPrimitive(value)}`);
}

function printResult(name, data, asJson) {
  if (asJson) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  console.log(`\n=== ${humanizeName(name)} ===`);
  printPretty(data, 0);
}

function parseArgs(argv) {
  const args = {
    list: false,
    all: false,
    pick: false,
    run: null,
    currency: "USD",
    location: "LOC-MEDELLIN-01",
    topN: 2,
    targetCapacity: 100,
    json: false,
    help: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--list") args.list = true;
    else if (token === "--all") args.all = true;
    else if (token === "--pick") args.pick = true;
    else if (token === "--help" || token === "-h") args.help = true;
    else if (token === "--run") args.run = argv[index + 1];
    else if (token === "--currency") args.currency = (argv[index + 1] || "USD").toUpperCase();
    else if (token === "--location") args.location = argv[index + 1] || args.location;
    else if (token === "--top-n") args.topN = Math.max(1, Number(argv[index + 1] || 2));
    else if (token === "--target-capacity") args.targetCapacity = Number(argv[index + 1] || 100);
    else if (token === "--json") args.json = true;
    else if (token === "--pretty") args.json = false;
  }

  return args;
}

async function pickArgsInteractively() {
  const rl = readline.createInterface({ input, output });

  try {
    console.log("\nBrasaland Functions Picker\n");

    const runMode = (
      await rl.question("Run mode ([o]ne / [m]ultiple / [a]ll) [o]: ")
    )
      .trim()
      .toLowerCase();

    let run = null;
    let all = false;

    if (runMode === "a" || runMode === "all") {
      all = true;
    } else {
      console.log("\nAvailable functions:");
      functionNames.forEach((name, index) => {
        console.log(`${index + 1}. ${name}`);
      });

      if (runMode === "m" || runMode === "multiple") {
        const multipleInput = await rl.question(
          "\nEnter numbers or names separated by commas (example: 1,5,calculateWasteCost): ",
        );
        const tokens = multipleInput
          .split(",")
          .map((token) => token.trim())
          .filter(Boolean)
          .map((token) => {
            const numeric = Number(token);
            if (Number.isInteger(numeric) && numeric >= 1 && numeric <= functionNames.length) {
              return functionNames[numeric - 1];
            }
            return token;
          });
        run = tokens.join(",");
      } else {
        const singleInput = await rl.question("\nChoose one function by number or name [1]: ");
        const chosen = singleInput.trim() || "1";
        const numeric = Number(chosen);
        if (Number.isInteger(numeric) && numeric >= 1 && numeric <= functionNames.length) {
          run = functionNames[numeric - 1];
        } else {
          run = chosen;
        }
      }
    }

    const currencyInput = (await rl.question("Currency (USD/COP) [USD]: ")).trim().toUpperCase();
    const locationInput = (await rl.question("Location ID [LOC-MEDELLIN-01]: ")).trim();
    const topNInput = (await rl.question("Top N [2]: ")).trim();
    const targetInput = (await rl.question("Target capacity [100]: ")).trim();
    const outputInput = (await rl.question("Output format ([p]retty / [j]son) [pretty]: "))
      .trim()
      .toLowerCase();

    return {
      list: false,
      all,
      pick: false,
      run,
      currency: currencyInput === "COP" ? "COP" : "USD",
      location: locationInput || "LOC-MEDELLIN-01",
      topN: Math.max(1, Number(topNInput || 2)),
      targetCapacity: Number(targetInput || 100),
      json: outputInput === "j" || outputInput === "json",
      help: false,
    };
  } finally {
    rl.close();
  }
}

function runByName(name, opts) {
  const sortedByCapacity = sortLocationsByCapacity(locations, "asc");
  const location = findLocationById(locations, opts.location) || locations[0];

  const runners = {
    filterSalesByLocation: () => filterSalesByLocation(sales, location.id),
    filterSalesByDateRange: () =>
      filterSalesByDateRange(sales, new Date("2024-03-15T00:00:00Z"), new Date("2024-03-15T23:59:59Z")),
    filterMenuItemsByCategory: () => filterMenuItemsByCategory(menuItems, "Meat"),
    filterActiveLocations: () => filterActiveLocations(locations),
    sortLocationsByCapacity: () => sortLocationsByCapacity(locations, "asc"),
    sortMenuItemsByPrice: () => sortMenuItemsByPrice(menuItems, opts.currency, "asc"),
    findLocationById: () => findLocationById(locations, location.id),
    findMenuItemByName: () => findMenuItemByName(menuItems, "french fries"),
    binarySearchLocationByCapacity: () => ({
      sortedByCapacity,
      targetCapacity: opts.targetCapacity,
      index: binarySearchLocationByCapacity(sortedByCapacity, opts.targetCapacity),
    }),
    calculateDailyRevenue: () => calculateDailyRevenue(sales, new Date("2024-03-15T00:00:00Z"), opts.currency),
    calculateLocationMargin: () => calculateLocationMargin(sales, menuItems, location.id, opts.currency),
    calculateWasteCost: () => calculateWasteCost(wasteRecords, location.id, opts.currency),
    convertCurrency: () => ({
      usdToCop: convertCurrency(25, "USD", "COP"),
      copToUsd: convertCurrency(100000, "COP", "USD"),
    }),
    scoreLocationPerformance: () => scoreLocationPerformance(location, sales, wasteRecords, menuItems),
    rankLocationsByPerformance: () => rankLocationsByPerformance(locations, sales, wasteRecords, menuItems),
    countSalesByPaymentMethod: () => countSalesByPaymentMethod(sales),
    calculateAverageTicket: () => calculateAverageTicket(sales, opts.currency),
    findTopSellingItems: () => findTopSellingItems(sales, menuItems, opts.topN),
    groupWasteByReason: () => groupWasteByReason(wasteRecords),
    calculateCountryComparison: () => calculateCountryComparison(sales, locations),
    validateMenuItem: () => validateMenuItem(menuItems[0]),
    validateSaleTransaction: () => validateSaleTransaction(sales[0]),
    validateLocation: () => validateLocation(location),
  };

  if (!runners[name]) {
    throw new Error(`Unknown function: ${name}`);
  }

  return runners[name]();
}

function printUsage() {
  console.log("Brasaland Functions CLI");
  console.log("");
  console.log("Usage:");
  console.log("  npm run functions:list");
  console.log("  npm run functions:run -- --run <functionName> [options]");
  console.log("  npm run functions:all -- [options]");
  console.log("  npm run functions:pick");
  console.log("");
  console.log("Options:");
  console.log("  --pick");
  console.log("  --currency USD|COP");
  console.log("  --location <LOCATION_ID>");
  console.log("  --top-n <number>");
  console.log("  --target-capacity <number>");
  console.log("  --json");
  console.log("  --pretty");
  console.log("  --help");
}

async function main() {
  let args = parseArgs(process.argv.slice(2));

  if (args.pick) {
    args = await pickArgsInteractively();
  }

  if (args.help) {
    printUsage();
    process.exit(0);
  }

  if (args.list) {
    functionNames.forEach((name, index) => {
      console.log(`${String(index + 1).padStart(2, " ")}. ${name}  ->  ${humanizeName(name)}`);
    });
    process.exit(0);
  }

  if (args.all) {
    const out = {};
    functionNames.forEach((name) => {
      out[name] = runByName(name, args);
    });
    if (args.json) {
      console.log(JSON.stringify(out, null, 2));
    } else {
      functionNames.forEach((name) => {
        printResult(name, out[name], false);
      });
    }
    process.exit(0);
  }

  if (args.run) {
    const runTargets = args.run
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);

    if (runTargets.length === 1) {
      const out = runByName(runTargets[0], args);
      printResult(runTargets[0], out, args.json);
    } else {
      const multiOut = {};
      runTargets.forEach((name) => {
        multiOut[name] = runByName(name, args);
      });

      if (args.json) {
        console.log(JSON.stringify(multiOut, null, 2));
      } else {
        runTargets.forEach((name) => {
          printResult(name, multiOut[name], false);
        });
      }
    }
    process.exit(0);
  }

  printUsage();
  process.exit(1);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
