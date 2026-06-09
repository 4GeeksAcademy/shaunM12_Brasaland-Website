#!/usr/bin/env node

const readline = require("node:readline/promises");
const { stdin: input, stdout: output } = require("node:process");
const { spawnSync } = require("node:child_process");

const ALIAS_TO_FUNCTION = {
  sales: "filterSalesByLocation",
  date: "filterSalesByDateRange",
  menu: "filterMenuItemsByCategory",
  active: "filterActiveLocations",
  capacity: "sortLocationsByCapacity",
  price: "sortMenuItemsByPrice",
  location: "findLocationById",
  item: "findMenuItemByName",
  binary: "binarySearchLocationByCapacity",
  revenue: "calculateDailyRevenue",
  margin: "calculateLocationMargin",
  waste: "calculateWasteCost",
  fx: "convertCurrency",
  score: "scoreLocationPerformance",
  rank: "rankLocationsByPerformance",
  payments: "countSalesByPaymentMethod",
  ticket: "calculateAverageTicket",
  top: "findTopSellingItems",
  wastegroup: "groupWasteByReason",
  countries: "calculateCountryComparison",
  "validate-menu": "validateMenuItem",
  "validate-sale": "validateSaleTransaction",
  "validate-location": "validateLocation",
};

function printHelp() {
  console.log("Brasaland Easy CLI");
  console.log("");
  console.log("Quick usage:");
  console.log("  npm run cli");
  console.log("  npm run cli -- help");
  console.log("  npm run cli -- list");
  console.log("  npm run cli -- filters [--location LOC-MIAMI-01]");
  console.log("  npm run cli -- health [--currency USD]");
  console.log("  npm run cli -- sales [--location LOC-MIAMI-01]");
  console.log("  npm run cli -- run <aliasOrFunctionName>");
  console.log("");
  console.log("Useful aliases:");
  console.log("  sales, date, menu, active, revenue, margin, waste, ticket, top, countries");
  console.log("");
  console.log("Extra options pass-through:");
  console.log("  --location <LOCATION_ID>");
  console.log("  --currency USD|COP");
  console.log("  --top-n <number>");
  console.log("  --target-capacity <number>");
  console.log("  --json");
}

function runFunctionsCli(args) {
  const result = spawnSync("node", ["scripts/functions-cli.cjs", ...args], {
    stdio: "inherit",
    cwd: process.cwd(),
  });

  if (typeof result.status === "number") {
    process.exit(result.status);
  }

  process.exit(1);
}

function parseCommonOptions(argv) {
  const args = [];

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (["--location", "--currency", "--top-n", "--target-capacity"].includes(token)) {
      args.push(token);
      args.push(argv[index + 1] || "");
      index += 1;
    } else if (["--json", "--pretty"].includes(token)) {
      args.push(token);
    }
  }

  return args;
}

function resolveFunctionName(token) {
  return ALIAS_TO_FUNCTION[token] || token;
}

async function interactiveMode() {
  const rl = readline.createInterface({ input, output });

  try {
    console.log("\nBrasaland Easy CLI");
    console.log("\n1) Run filtering set");
    console.log("2) Run sales health set");
    console.log("3) Pick one function");
    console.log("4) Show all functions");
    console.log("5) Exit\n");

    const choice = (await rl.question("Choose option [1]: ")).trim() || "1";

    if (choice === "1") {
      runFunctionsCli([
        "--run",
        "filterSalesByLocation,filterSalesByDateRange,filterMenuItemsByCategory,filterActiveLocations",
      ]);
      return;
    }

    if (choice === "2") {
      runFunctionsCli([
        "--run",
        "calculateDailyRevenue,calculateLocationMargin,calculateWasteCost,calculateAverageTicket",
      ]);
      return;
    }

    if (choice === "3") {
      runFunctionsCli(["--pick"]);
      return;
    }

    if (choice === "4") {
      runFunctionsCli(["--list"]);
      return;
    }
  } finally {
    rl.close();
  }
}

async function main() {
  const [, , command, ...rest] = process.argv;
  const commonOptions = parseCommonOptions(rest);

  if (!command) {
    await interactiveMode();
    return;
  }

  if (command === "help" || command === "-h" || command === "--help") {
    printHelp();
    return;
  }

  if (command === "list") {
    runFunctionsCli(["--list"]);
    return;
  }

  if (command === "all") {
    runFunctionsCli(["--all", ...commonOptions]);
    return;
  }

  if (command === "filters") {
    runFunctionsCli([
      "--run",
      "filterSalesByLocation,filterSalesByDateRange,filterMenuItemsByCategory,filterActiveLocations",
      ...commonOptions,
    ]);
    return;
  }

  if (command === "health") {
    runFunctionsCli([
      "--run",
      "calculateDailyRevenue,calculateLocationMargin,calculateWasteCost,calculateAverageTicket",
      ...commonOptions,
    ]);
    return;
  }

  if (command === "sales") {
    runFunctionsCli(["--run", "filterSalesByLocation", ...commonOptions]);
    return;
  }

  if (command === "run") {
    const target = rest[0];

    if (!target) {
      console.error("Missing function name or alias. Example: npm run cli -- run margin");
      process.exit(1);
    }

    runFunctionsCli(["--run", resolveFunctionName(target), ...commonOptions]);
    return;
  }

  runFunctionsCli(["--run", resolveFunctionName(command), ...commonOptions]);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
