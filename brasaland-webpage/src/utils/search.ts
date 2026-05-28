import { BrasaLocation, BrasaPointsRegistration } from "../types/models.js";

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

export function findRegistrationByEmail(
  registrations: BrasaPointsRegistration[],
  email: string,
): BrasaPointsRegistration | null {
  const normalizedEmail = normalize(email);
  const registration = registrations.find(
    (currentRegistration) => normalize(currentRegistration.email) === normalizedEmail,
  );

  return registration ?? null;
}

export function findLocationByName(
  locations: BrasaLocation[],
  locationName: string,
): BrasaLocation | null {
  const normalizedName = normalize(locationName);
  const location = locations.find((currentLocation) => normalize(currentLocation.name) === normalizedName);

  return location ?? null;
}

export function binarySearchRegistrationByEmail(
  sortedRegistrations: BrasaPointsRegistration[],
  targetEmail: string,
): number {
  const normalizedTargetEmail = normalize(targetEmail);
  let startIndex = 0;
  let endIndex = sortedRegistrations.length - 1;

  while (startIndex <= endIndex) {
    const middleIndex = Math.floor((startIndex + endIndex) / 2);
    const middleEmail = normalize(sortedRegistrations[middleIndex].email);

    if (middleEmail === normalizedTargetEmail) {
      return middleIndex;
    }

    if (middleEmail < normalizedTargetEmail) {
      startIndex = middleIndex + 1;
    } else {
      endIndex = middleIndex - 1;
    }
  }

  return -1;
}

export function binarySearchLocationByName(
  sortedLocations: BrasaLocation[],
  targetLocationName: string,
): number {
  const normalizedTargetName = normalize(targetLocationName);
  let startIndex = 0;
  let endIndex = sortedLocations.length - 1;

  while (startIndex <= endIndex) {
    const middleIndex = Math.floor((startIndex + endIndex) / 2);
    const middleName = normalize(sortedLocations[middleIndex].name);

    if (middleName === normalizedTargetName) {
      return middleIndex;
    }

    if (middleName < normalizedTargetName) {
      startIndex = middleIndex + 1;
    } else {
      endIndex = middleIndex - 1;
    }
  }

  return -1;
}
