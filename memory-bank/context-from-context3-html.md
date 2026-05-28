# CONTEXT - Brasaland

## AI Engineering - 4Geeks Academy

> Source: context files/context3.html

### Milestone Focus

Milestone 2: Programming Fundamentals.

---

## Company Overview

- **Company:** Brasaland (grilled food restaurant chain)
- **Role:** Junior Developer, Brasaland Digital Team
- **Project Owner:** Felipe Guerrero, Operations Director
- **Footprint:** 14 company-owned locations across Colombia and USA (Florida)

Brasaland focuses on consistent product quality, warm customer experience, and speed of service. You are building internal digital tools to modernize operations.

---

## Assignment

Felipe needs core data-processing logic for Brasaland operations. Managers currently track sales, margins, waste, and ingredient ordering manually. This milestone focuses on TypeScript utilities for sales analytics, waste control, and performance scoring.

---

## What You Are Building

Implement TypeScript utilities to:

- Model menu items, sales, and locations with interfaces
- Filter and search sales data by location, date, and product
- Calculate location performance scores using multiple metrics
- Compute financial metrics in USD and COP
- Generate aggregated operations reports
- Validate business data before processing

---

## Business Entities

### Menu Item

```ts
interface MenuItem {
  id: string;
  name: string;
  category: MenuCategory;
  basePrice: Price;
  ingredientCost: Price;
  prepTimeMinutes: number;
  isAvailableInColombia: boolean;
  isAvailableInUSA: boolean;
  allergens: string[];
  status: MenuItemStatus;
}

interface Price {
  USD: number;
  COP: number;
}

type MenuCategory = "Meat" | "Side" | "Beverage" | "Dessert" | "Combo";
type MenuItemStatus = "Active" | "Seasonal" | "Discontinued";
```

Validation rules:

- USD and COP prices must be `> 0`
- `prepTimeMinutes` must be `> 0` and `<= 60`
- `name` must not be empty
- Item must be available in at least one country

### Sale Transaction

```ts
interface SaleTransaction {
  id: string;
  locationId: string;
  itemId: string;
  quantity: number;
  totalPrice: Price;
  paymentMethod: PaymentMethod;
  timestamp: Date;
  waiterName: string;
}

type PaymentMethod = "Cash" | "Credit card" | "Debit card" | "Digital wallet";
```

Validation rules:

- `quantity > 0`
- both price values `> 0`
- `waiterName` must not be empty

### Location

```ts
interface Location {
  id: string;
  name: string;
  city: string;
  country: Country;
  openingYear: number;
  seatingCapacity: number;
  staffCount: number;
  monthlyRentCost: Price;
  averageMonthlyUtilities: Price;
  manager: string;
  status: LocationStatus;
}

type Country = "Colombia" | "USA";
type LocationStatus = "Active" | "Temporarily closed" | "Under renovation";
```

Validation rules:

- `openingYear >= 2008` and `<= current year`
- `seatingCapacity > 0`
- `staffCount > 0`
- rent and utilities prices `> 0`

### Waste Record

```ts
interface WasteRecord {
  id: string;
  locationId: string;
  itemId: string;
  quantity: number;
  reason: WasteReason;
  cost: Price;
  timestamp: Date;
  reportedBy: string;
}

type WasteReason = "Expired" | "Cooking error" | "Customer return" | "Damage" | "Other";
```

---

## Required Functions

### Collection Operations

File: `Brasaland webpage/src/utils/collections.ts`

- `filterSalesByLocation(sales, locationId): SaleTransaction[]`
- `filterSalesByDateRange(sales, startDate, endDate): SaleTransaction[]`
- `filterMenuItemsByCategory(items, category): MenuItem[]`
- `filterActiveLocations(locations): Location[]`
- `sortLocationsByCapacity(locations, order): Location[]` (no mutation)
- `sortMenuItemsByPrice(items, currency, order): MenuItem[]` (no mutation)

### Search Operations

File: `Brasaland webpage/src/utils/search.ts`

- `findLocationById(locations, id): Location | null` (linear search)
- `findMenuItemByName(items, name): MenuItem | null` (case-insensitive)
- `binarySearchLocationByCapacity(sortedLocations, targetCapacity): number` (ascending array, index or `-1`)

### Financial Calculations

File: `Brasaland webpage/src/utils/transformations.ts`

- `calculateDailyRevenue(sales, date, currency): number` (2 decimals)
- `calculateLocationMargin(sales, menuItems, locationId, currency): number`
- `calculateWasteCost(wasteRecords, locationId, currency): number` (2 decimals)
- `convertCurrency(amount, fromCurrency, toCurrency): number`

Currency rule:

- Fixed rate: `1 USD = 4000 COP`
- Return 2 decimals
- If same currency, return original amount

### Location Performance Scoring

File: `Brasaland webpage/src/utils/transformations.ts`

- `scoreLocationPerformance(location, sales, wasteRecords, menuItems): number`
- `rankLocationsByPerformance(locations, sales, wasteRecords, menuItems): Array<{ location: Location; score: number }>`

Scoring model (0-100):

- Revenue performance: max 40
- Efficiency: max 30
- Waste control: max 20
- Profit margin: max 10

Return score rounded to 2 decimals.

### Aggregations and Reports

File: `Brasaland webpage/src/utils/transformations.ts`

- `countSalesByPaymentMethod(sales): Record<PaymentMethod, number>`
- `calculateAverageTicket(sales, currency): number` (2 decimals)
- `findTopSellingItems(sales, menuItems, topN): Array<{ item: MenuItem; totalSold: number }>`
- `groupWasteByReason(wasteRecords): Record<WasteReason, WasteRecord[]>`
- `calculateCountryComparison(sales, locations, menuItems): { Colombia: CountryMetrics; USA: CountryMetrics }`

```ts
interface CountryMetrics {
  totalLocations: number;
  totalRevenue: Price;
  averageRevenuePerLocation: Price;
  totalSales: number;
}
```

### Validations

File: `Brasaland webpage/src/utils/validations.ts`

- `validateMenuItem(item): { valid: boolean; errors: string[] }`
- `validateSaleTransaction(sale): { valid: boolean; errors: string[] }`
- `validateLocation(location): { valid: boolean; errors: string[] }`

---

## Sample Data

### Sample Menu Items

```ts
const sampleMenuItems: MenuItem[] = [
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
```

### Sample Locations

```ts
const sampleLocations: Location[] = [
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
```

### Sample Sales

```ts
const sampleSales: SaleTransaction[] = [
  {
    id: "TXN-2024-15482",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 2,
    totalPrice: { USD: 37.0, COP: 148000 },
    paymentMethod: "Credit card",
    timestamp: new Date("2024-03-15T19:30:00"),
    waiterName: "Maria Gonzalez",
  },
  {
    id: "TXN-2024-15483",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-FRIES",
    quantity: 3,
    totalPrice: { USD: 13.5, COP: 54000 },
    paymentMethod: "Cash",
    timestamp: new Date("2024-03-15T20:15:00"),
    waiterName: "John Smith",
  },
];
```

---

## Acceptance Criteria

Implementation is evaluated on:

- Type safety for all interfaces and aliases
- Full required-function coverage
- Correct outputs for sample inputs
- Graceful edge-case handling (empty arrays, missing matches)
- Correct validation logic and structured errors
- Correct file organization by responsibility
- Clear TypeScript naming conventions
- No mutation in sort/filter utilities
- Single-responsibility function design
- Pure-function behavior (no hidden global state)
- Accurate USD/COP handling and conversion
- Clear development commands for type-check/run

---

## Stakeholder Expectation

> "Mira, we have 14 locations running every day. Your code needs to handle Colombian pesos and US dollars correctly, work with different time zones, and give me accurate numbers I can trust. No shortcuts. If the margin calculation is wrong, I'm making bad decisions. Build it right."
>
> - Felipe Guerrero, Operations Director
