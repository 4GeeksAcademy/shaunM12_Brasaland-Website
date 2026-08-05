# Milestone 1 — Public Website + Brasa Points Registration

## AI Engineering — 4Geeks Academy

> **Canonical Milestone 1 spec.** Root [`CONTEXT.md`](../../CONTEXT.md) is repo-wide company context only. For M1 website and Brasa Points form work, **this file is authoritative**.

> This document describes the company situation and requirements for Milestone 1. Read it completely before writing any code. Everything you build must reflect this context.

---

## Milestone focus

Relaunch Brasaland's public corporate website and Brasa Points registration flow.

---

## Your company

**Brasaland** is a grilled food restaurant chain founded in 2008 in Medellín, Colombia. What began as a single family-run location has grown into a chain of 14 company-owned restaurants operating in Colombia and the United States (Florida). The company employs approximately 115 people between kitchen and floor staff, operations management, and the corporate team headquartered in Medellín with a commercial office in Miami. Annual revenue sits around 6 million dollars. The brand is built on three pillars: consistent product quality across every location, a warm and reliable customer experience, and speed of service.

---

## Your department and the problem you must solve

You work in **Brasaland Digital**, the internal team created by CEO Mariana Restrepo to lead the company's digital transformation, and you report directly to CTO Nicolás Park. Brasaland's current corporate website is from 2019, doesn't allow online orders, and only shows the menu. It doesn't reflect that the company operates in two countries or properly present the brand experience. Camila Ospina (Marketing Manager) needs a renewed website that professionally presents the brand, shows locations in both countries, and captures information from people interested in joining the digital loyalty program.

For this milestone, stakeholder priority is to relaunch Brasaland's public website so it:

- Represents Brasaland as a serious two-country restaurant chain
- Clearly presents value proposition and locations
- Introduces Brasa Points (digital loyalty program)
- Captures validated customer registration data

---

## Your stakeholder

**Camila Ospina**, Marketing Manager

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

## Location names (course vs monorepo)

The course brief below uses **marketing neighborhood names** (El Poblado, Coral Gables, etc.) and a simplified city list (Medellín, Bogotá, Cali, Miami, Orlando).

The **monorepo canonical list** for backend, inventory, agent, and website form logic is:

- `packages/shared/restaurant_locations.py` (Python, IDs 1–14)
- `uis/website/lib/restaurant-locations.ts` (website)

When implementing in this repository, follow the **code canonical list** for dependent selects and location IDs. Use the course copy below for landing-page marketing blurbs where they do not conflict with live location data.

---

## Language scope

- Multilingual support is **optional but highly recommended** given Brasaland's operations in Colombia and the United States.
- You must choose one **base language** for the full website and form experience.
- If you implement a second language, treat it as an enhancement (do not reduce quality/completeness in the base language).

---

## Landing page content

Your landing page must include the following sections, in this order:

### Header

- Logo or name "Brasaland"
- Language selector (ES | EN) if you implement a second language
- Navigation: Home | Locations | Menu | Brasa Points | Contact

### Hero

- **Headline:** "The taste of the grill, in every bite"
- **Subheadline:** "Since 2008 serving the best grilled meats in Colombia and the United States. 14 locations, one passion for quality and flavor."
- **Call to action:** Button "Join Brasa Points" linking to the form

### Our Story (paragraph + image)

Founded in Medellín in 2008, Brasaland began as a family dream: sharing the authentic taste of grilled meat with consistent quality and warm service. Today we are 14 restaurants in two countries, but we maintain the same recipe for success: fresh products, traditional techniques, and passion for every dish we serve.

### What Makes Us Unique (3 columns)

1. **Consistent Quality**
   - Same recipes and standards in all locations
   - Fresh ingredients selected daily
2. **Warm Experience**
   - Friendly and attentive service
   - Family atmosphere on every visit
3. **Speed**
   - Your food ready in minutes
   - Without sacrificing flavor or quality

### Our Locations (2 columns)

- **Colombia**
  - 10 restaurants in Medellín, Bogotá and Cali
  - Hours: Mon-Sun 11:00 AM - 10:00 PM

- **United States (Florida)**
  - 4 restaurants in Miami and Orlando
  - Hours: Mon-Sun 11:00 AM - 10:00 PM

### Brasa Points (featured section)

#### Earn points with every visit

- Accumulate 1 point for every $10,000 COP or $5 USD
- Redeem your points for discounts and free dishes
- Exclusive offers for members
- 100% digital registration - no more paper cards!

### Contact

- Email: hello@brasaland.com
- Colombia: +57 4 123 4567
- Florida: +1 305 123 4567

### Footer

- © 2025 Brasaland. All rights reserved.
- Instagram | Facebook

---

## Brasa Points registration form fields

Your form must capture the following information:

| Field | Type | Validation | Required |
| --- | --- | --- | --- |
| **Full name** | text | Minimum 2 words | Yes |
| **Email** | email | Valid email format | Yes |
| **Phone** | tel | Format: +[country code] [number] | Yes |
| **Country** | select | Colombia / United States | Yes |
| **City** | select | Medellín / Bogotá / Cali / Miami / Orlando (per country) | Yes |
| **Favorite Brasaland location** | select | List of 14 restaurants per country and city | No |
| **Dietary preferences** | checkbox | No restrictions / Vegetarian / Gluten-free / Other | No |
| **How did you find us?** | select | Social media / Recommendation / Walked by / Internet search / Other | Yes |
| **Date of birth** | date | Must be 18 or older | Yes |
| **I accept program terms** | checkbox | Must be checked to submit | Yes |
| **I want to receive offers via email** | checkbox | Optional, unchecked by default | No |

---

## Specific validations

1. **Full name:** Must contain at least first and last name
2. **Email:** Must be valid format (contain @ and domain)
3. **Phone:** Must start with + followed by country code (+57 for Colombia, +1 for USA)
4. **City:** City options must change dynamically based on selected country
5. **Favorite location:** Options must filter based on selected country and city
6. **Date of birth:** User must be 18 or older (validate date)
7. **Program terms:** Checkbox must be checked to submit

---

## Dependent field logic (course brief)

**Country → City:**

- If selecting "Colombia": show Medellín, Bogotá, Cali
- If selecting "United States": show Miami, Orlando

**Country + City → Favorite location:**

- Colombia - Medellín: Brasaland El Poblado, Brasaland Laureles, Brasaland Envigado, Brasaland Sabaneta
- Colombia - Bogotá: Brasaland Usaquén, Brasaland Chapinero, Brasaland Zona Rosa
- Colombia - Cali: Brasaland Granada, Brasaland Ciudad Jardín, Brasaland Unicentro
- USA - Miami: Brasaland Brickell, Brasaland Coral Gables
- USA - Orlando: Brasaland Downtown, Brasaland International Drive

> In this monorepo, form dependent selects follow `uis/website/lib/restaurant-locations.ts` instead of the course neighborhood names above.

---

## Expected error messages

When a field doesn't meet validation, display these specific messages:

- **Full name:** "Enter your full name (first and last name)"
- **Email:** "Enter a valid email (example: name@email.com)"
- **Phone:** "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)"
- **Country:** "Select your country"
- **City:** "Select your city"
- **How did you find us:** "Tell us how you found Brasaland"
- **Date of birth:** "You must be 18 or older to register for Brasa Points"
- **Program terms:** "You must accept the Brasa Points program terms to continue"

---

## Success message

When the form validates correctly (simulate submission), display:

> **Welcome to Brasa Points!**
>
> Your registration was successful. You will receive a confirmation email in the next few minutes with your account details and how to start earning points.
>
> You can now enjoy your benefits at any of our 14 locations!

---

## Specific restriction

The Brasa Points program is designed for **customers 18 or older who want to earn points with their visits**. It is not a reservation or online ordering form. The site must include a visible message that says: "Want to place an order? Call your favorite location or visit us directly. Online ordering coming soon!"

---

## Required Schema.org markup

Implement the following Schema.org markup on your landing page.

If you deliver only one language, set `availableLanguage` to just that base language.

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
      "addressLocality": "Medellín",
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
