# CONTEXT - Brasaland

## AI Engineering - 4Geeks Academy

_These instructions are also available in Spanish in the project docs._

> This document describes your company and the specific situation you are building this milestone for. Read it completely before writing any code. Everything you build must reflect this context.

> Source: merged from context files/context.html and CONTEXT.md

### Milestone Focus

Consolidated briefing (company context + Milestone 1 requirements).

---

## Company Overview

Brasaland is a grilled food restaurant chain founded in 2008 in Medellin, Colombia. What started as a single family-run location became a 14-location chain operating in Colombia and the United States (Florida). The company employs around 115 people and generates approximately 6 million USD in annual revenue.

The brand is built on three pillars:

- Consistent product quality in every location
- Warm, reliable customer experience
- Speed of service without sacrificing quality

Brasaland is led by CEO Mariana Restrepo. The company headquarters is in Medellin, with a commercial and operations office in Miami. To modernize operations, leadership created an internal transformation team: **Brasaland Digital**.

---

## Operating Context and Current Problems

Brasaland remains profitable, but many critical processes are still manual (spreadsheets, email, WhatsApp, disconnected systems). This creates visibility gaps and slower decision-making across two countries.

### Restaurant Operations

**Lead:** Felipe Guerrero

- Locations operate with limited real-time visibility
- Ingredient ordering is mostly manual
- Reporting is fragmented and delayed

### Procurement and Suppliers

**Lead:** Lucia Fernandez

- Around 20 suppliers across both markets
- Negotiation and tracking rely on email + spreadsheets
- No consolidated purchasing intelligence

### Marketing and Digital Experience

**Lead:** Camila Ospina

- Website is outdated and lacks modern conversion flows
- Loyalty program is physical-card based, generates little data
- Minimal customer-level insight

### People and Culture

**Lead:** Ashley Turner

- HR processes are mostly manual
- Two-country labor context increases operational complexity

### Training and Quality Standards

**Lead:** Jake Morrison

- Training material distribution is hard to maintain
- Update communication is slow across locations/countries

### Technology

**Lead:** CTO Nicolas Park

- Minimal shared platform
- No unified internal API/data layer
- Limited telemetry and integration

### Executive Direction

**Lead:** CEO Mariana Restrepo

- Strategic decisions are delayed by fragmented reporting
- No centralized, near real-time view of business performance

---

## Milestone 1 Scope: Public Website + Brasa Points Registration

You work in **Brasaland Digital** and report to CTO Nicolas Park.

### Department and Problem Statement

Brasaland's current corporate website is from 2019, does not allow online orders, and mostly shows menu information. It does not fully reflect that the company operates in two countries or communicate the full brand experience.

Marketing needs a renewed website that professionally presents the brand, shows locations in both countries, and captures information from people interested in joining Brasa Points.

For this milestone, stakeholder priority is to relaunch Brasaland's public website so it:

- Represents Brasaland as a serious two-country restaurant chain
- Clearly presents value proposition and locations
- Introduces Brasa Points (digital loyalty program)
- Captures validated customer registration data

### Primary Stakeholder

**Camila Ospina, Marketing Manager**

Stakeholder request (verbatim):

> Hi,
>
> We need to relaunch our corporate website. It should present Brasaland as what we are: a serious grilled food restaurant chain with presence in Colombia and the United States. I want a landing page that explains our value proposition, shows our locations in both countries, and presents our new digital loyalty program "Brasa Points." I also need a page with a form so people can register for the loyalty program. We currently use physical stamp cards that get lost and generate no data. I want to capture: name, email, phone, country, city, favorite location, dietary preferences, and how they found us. The site must be responsive, accessible, and SEO optimized. Multilingual support (Spanish and English) is optional but highly recommended; start with one base language. Use Tailwind and make sure the validations work perfectly.

Requested outcome:

- Professional landing page
- Locations in Colombia and US
- Brasa Points featured section
- Registration form with strict validations
- Responsive, accessible, SEO-optimized implementation
- Optional but recommended bilingual support (ES/EN)

---

## Language Scope

- Multilingual support is **optional but highly recommended**
- Choose one **base language** for complete delivery
- If you add a second language, treat it as enhancement (base language quality cannot drop)

---

## Landing Page Requirements (Order Matters)

### Header

- Logo or text brand: "Brasaland"
- Language selector (ES | EN) if bilingual is implemented
- Navigation: Home | Locations | Menu | Brasa Points | Contact

### Hero

- Headline: "The taste of the grill, in every bite"
- Subheadline: "Since 2008 serving the best grilled meats in Colombia and the United States. 14 locations, one passion for quality and flavor."
- CTA button: "Join Brasa Points" linking to the form

### Our Story (Paragraph + Image)

Founded in Medellin in 2008, Brasaland began as a family dream: sharing the authentic taste of grilled meat with consistent quality and warm service. Today we are 14 restaurants in two countries, but we maintain the same recipe for success: fresh products, traditional techniques, and passion for every dish we serve.

### What Makes Us Unique (3 Columns)

1. **Consistent Quality**
   - Same recipes and standards in all locations
   - Fresh ingredients selected daily
2. **Warm Experience**
   - Friendly and attentive service
   - Family atmosphere on every visit
3. **Speed**
   - Your food ready in minutes
   - Without sacrificing flavor or quality

### Our Locations (2 Columns)

- **Colombia**
  - 10 restaurants in Medellin, Bogota and Cali
  - Hours: Mon-Sun 11:00 AM - 10:00 PM

- **United States (Florida)**
  - 4 restaurants in Miami and Orlando
  - Hours: Mon-Sun 11:00 AM - 10:00 PM

### Brasa Points (Featured Section)

#### Earn Points With Every Visit

- Accumulate 1 point for every $10,000 COP or $5 USD
- Redeem your points for discounts and free dishes
- Exclusive offers for members
- 100% digital registration - no more paper cards

### Contact

- Email: hello@brasaland.com
- Colombia: +57 4 123 4567
- Florida: +1 305 123 4567

### Footer

- Copyright 2025 Brasaland. All rights reserved.
- Instagram | Facebook

---

## Brasa Points Registration Form Requirements

| Field | Type | Validation | Required |
| --- | --- | --- | --- |
| Full name | text | Minimum 2 words | Yes |
| Email | email | Valid email format | Yes |
| Phone | tel | Format: +[country code] [number] | Yes |
| Country | select | Colombia / United States | Yes |
| City | select | Medellin / Bogota / Cali / Miami / Orlando (by country) | Yes |
| Favorite Brasaland location | select | 14-location list filtered by country and city | No |
| Dietary preferences | checkbox | No restrictions / Vegetarian / Gluten-free / Other | No |
| How did you find us? | select | Social media / Recommendation / Walked by / Internet search / Other | Yes |
| Date of birth | date | Must be 18+ | Yes |
| I accept program terms | checkbox | Must be checked | Yes |
| I want to receive offers via email | checkbox | Optional, unchecked by default | No |

---

## Specific Validation Rules

1. Full name: must include at least first and last name
2. Email: must be valid format (contains @ and domain)
3. Phone: must start with + and valid country code (+57 Colombia, +1 USA)
4. City: options depend on selected country
5. Favorite location: options depend on selected country + city
6. Date of birth: user must be 18+
7. Program terms: checkbox must be selected before submit

---

## Dependent Field Logic

### Country → City

- Colombia -> Medellin, Bogota, Cali
- United States -> Miami, Orlando

### Country + City → Favorite Location

- Colombia - Medellin: Brasaland El Poblado, Brasaland Laureles, Brasaland Envigado, Brasaland Sabaneta
- Colombia - Bogota: Brasaland Usaquen, Brasaland Chapinero, Brasaland Zona Rosa
- Colombia - Cali: Brasaland Granada, Brasaland Ciudad Jardin, Brasaland Unicentro
- USA - Miami: Brasaland Brickell, Brasaland Coral Gables
- USA - Orlando: Brasaland Downtown, Brasaland International Drive

---

## Expected Error Messages

- Full name: "Enter your full name (first and last name)"
- Email: "Enter a valid email (example: name@email.com)"
- Phone: "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)"
- Country: "Select your country"
- City: "Select your city"
- How did you find us: "Tell us how you found Brasaland"
- Date of birth: "You must be 18 or older to register for Brasa Points"
- Program terms: "You must accept the Brasa Points program terms to continue"

---

## Success Message

When validation passes (simulated submission), show:

> **Welcome to Brasa Points!**
>
> Your registration was successful. You will receive a confirmation email in the next few minutes with your account details and how to start earning points.
>
> You can now enjoy your benefits at any of our 14 locations.

---

## Program Restriction

Brasa Points is for **customers aged 18+** who want to earn points from visits. It is not a reservation or ordering form.

The site must include this visible message:

"Want to place an order? Call your favorite location or visit us directly. Online ordering coming soon!"

---

## Required Schema.org Markup

If you deliver a single language, set `availableLanguage` accordingly.

```json
{
  "@context": "https://schema.org",
  "@type": "Restaurant",
  "name": "Brasaland",
  "description": "Grilled food restaurant chain in Colombia and the United States",
  "url": "https://brasaland.com",
  "foundingDate": "2008",
  "servesCuisine": "Grilled food, Colombian cuisine",
  "priceRange": "$$",
  "address": [
    {
      "@type": "PostalAddress",
      "addressCountry": "CO",
      "addressLocality": "Medellin",
      "addressRegion": "Antioquia"
    },
    {
      "@type": "PostalAddress",
      "addressCountry": "US",
      "addressLocality": "Miami",
      "addressRegion": "FL"
    }
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+57-4-123-4567",
    "contactType": "customer service",
    "availableLanguage": ["Spanish", "English"]
  },
  "sameAs": [
    "https://instagram.com/brasaland",
    "https://facebook.com/brasaland"
  ]
}
```

---

_Internal document — 4Geeks Academy · AI Engineering Track_