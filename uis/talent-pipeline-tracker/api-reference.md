# Talent Pipeline Tracker API Reference

This document provides a comprehensive reference for interacting with the Talent Pipeline Tracker API. It includes all available endpoints, their parameters, expected responses, and status codes.

---

## Base URL

```
https://playground.4geeks.com/tracker/api/v1
```

---

## Endpoints

### 1. Records

#### **GET /records**
Retrieve a list of records.

**Query Parameters:**
- `status` (string, optional): Filter by status (`received`, `in_progress`, `selected`, `discarded`).
- `stage` (string, optional): Filter by stage (`pending`, `review`, `personal_interview`, `technical_interview`, `offer_presented`).
- `search` (string, optional): Search by `full_name` or `email`.
- `page` (integer, optional): Page number (default: 1).
- `limit` (integer, optional): Results per page (default: 20, minimum: 1).

**Responses:**
- `200 OK`: Successful response with a list of records.
- `422 Validation Error`: Invalid query parameters.

---

#### **POST /records**
Create a new record.

**Request Body:**
```json
{
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "position": "string",
  "linkedin_url": "string",
  "cv_url": "string",
  "status": "string",
  "stage": "string",
  "experience_years": 0
}
```

**Responses:**
- `201 Created`: Record successfully created.
- `422 Validation Error`: Invalid request body.

---

#### **GET /records/{id}**
Retrieve a specific record by ID.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Responses:**
- `200 OK`: Successful response with the record details.
- `422 Validation Error`: Invalid or missing `id`.

---

#### **PUT /records/{id}**
Replace a record by ID.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Request Body:**
```json
{
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "position": "string",
  "linkedin_url": "string",
  "cv_url": "string",
  "status": "string",
  "stage": "string",
  "experience_years": 0
}
```

**Responses:**
- `200 OK`: Record successfully replaced.
- `422 Validation Error`: Invalid request body or `id`.

---

#### **PATCH /records/{id}**
Update specific fields of a record by ID.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Request Body:**
```json
{
  "status": "string",
  "stage": "string"
}
```

**Responses:**
- `200 OK`: Record successfully updated.
- `422 Validation Error`: Invalid request body or `id`.

---

#### **DELETE /records/{id}**
Delete a record by ID.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Responses:**
- `204 No Content`: Record successfully deleted.
- `422 Validation Error`: Invalid or missing `id`.

---

### 2. Notes

#### **GET /records/{id}/notes**
Retrieve all notes for a specific record.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Responses:**
- `200 OK`: Successful response with a list of notes.
- `422 Validation Error`: Invalid or missing `id`.

---

#### **POST /records/{id}/notes**
Add a note to a specific record.

**Path Parameters:**
- `id` (string, required): The ID of the record.

**Request Body:**
```json
{
  "content": "string"
}
```

**Responses:**
- `201 Created`: Note successfully added.
- `422 Validation Error`: Invalid request body or `id`.

---

#### **DELETE /records/{id}/notes/{note_id}**
Delete a specific note for a record.

**Path Parameters:**
- `id` (string, required): The ID of the record.
- `note_id` (string, required): The ID of the note.

**Responses:**
- `204 No Content`: Note successfully deleted.
- `422 Validation Error`: Invalid or missing `id` or `note_id`.

---

## Testing the API

To test the API, you can use tools like:
- **Postman**: Create a collection with the above endpoints and test each method.
- **curl**: Use the command line to send HTTP requests.
- **Automated Tests**: Write test scripts in your preferred language (e.g., Python, JavaScript).

If you need help generating code or test scripts, let me know!