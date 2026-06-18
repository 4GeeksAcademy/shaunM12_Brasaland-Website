#!/usr/bin/env python3
"""Build context-5 English incidents-brasaland.csv from Spanish source data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from incident_analyzer import normalize_category, normalize_status  # noqa: E402

SOURCE = Path(__file__).parent / "source-incidents-spanish.csv"
OUTPUT = Path(__file__).parent / "incidents-brasaland.csv"

DESCRIPTION_TRANSLATIONS = {
    "Porción servida menor a la estándar del menú": "Portion served below menu standard",
    "Bajo stock de carbón para parrillas, pedido urgente enviado": "Low charcoal stock for grills, urgent order placed",
    "Proveedor de salsas no entregó el pedido semanal": "Sauce supplier did not deliver weekly order",
    "Queja por ruido excesivo en el área de mesas": "Complaint about excessive noise in dining area",
    "Lavaplatos industrial con fuga de agua detectada": "Industrial dishwasher water leak detected",
    "Cliente insatisfecho con el tiempo de espera en mesa": "Customer dissatisfied with table wait time",
    "Reclamación por reserva no encontrada al llegar": "Claim for reservation not found on arrival",
    "Cliente reporta alimento frío al momento de servir": "Customer reports cold food at serving time",
    "Faltante de bebidas importadas en carta": "Shortage of imported beverages on menu",
    "Falta de carne de res para cortes del menú principal": "Shortage of beef for main menu cuts",
    "Retraso en entrega de insumos de limpieza": "Delay in cleaning supply delivery",
    "Empleado no siguió protocolo de uniformidad": "Employee did not follow uniform protocol",
    "Desabasto de envases para pedidos para llevar": "Shortage of takeout packaging",
    "Sistema de música del local apagado sin respuesta": "Venue music system off without response",
    "Refrigerador de bebidas no enfría correctamente": "Beverage refrigerator not cooling properly",
    "Producto vencido detectado durante revisión de inventario": "Expired product found during inventory review",
    "Falla en la parrilla principal de cocina": "Main kitchen grill failure",
    "Terminal POS con error al procesar pagos con tarjeta": "POS terminal error processing card payments",
    "Salsa de la casa con sabor diferente al habitual": "House sauce tastes different than usual",
    "Empleado llegó tarde al turno de apertura": "Employee arrived late for opening shift",
    "Carne servida en término incorrecto según pedido": "Meat served at incorrect doneness per order",
    "Cliente informa que su pedido tardó más de 40 minutos": "Customer reports order took over 40 minutes",
    "Cliente insatisfecho con el servicio recibido": "Customer dissatisfied with service received",
    "Incidencia sin categorizar reportada por supervisor": "Uncategorized incident reported by supervisor",
    "Cliente reporta error en la cuenta cobrada": "Customer reports billing error",
    "Queja por temperatura inadecuada del local": "Complaint about inadequate venue temperature",
    "Solicitud de devolución por pedido incorrecto entregado": "Refund request for incorrect order delivered",
    "Queja por trato irrespetuoso del personal de sala": "Complaint about disrespectful floor staff behavior",
    "Guarnición servida sin cocción completa": "Side dish served undercooked",
    "Queja de cliente sobre comportamiento de mesero": "Customer complaint about server behavior",
    "Revisión de temperatura completada sin novedad": "Temperature review completed without issues",
    "Extractor de humos con funcionamiento deficiente": "Vent hood operating poorly",
    "No se recibió el pedido de vegetales frescos del día": "Daily fresh vegetable order not received",
}


def translate_description(text: str) -> str:
    cleaned = text.strip()
    return DESCRIPTION_TRANSLATIONS.get(cleaned, cleaned)


def build() -> None:
    df = pd.read_csv(SOURCE)
    rows: list[dict[str, object]] = []

    for _, row in df.iterrows():
        location_id = str(row["location_id"]).strip() if pd.notna(row.get("location_id")) else ""
        category = normalize_category(row.get("category")) or row.get("category", "")
        status = normalize_status(row.get("status")) or row.get("status", "")

        satisfaction = row.get("satisfaction_score")
        if pd.isna(satisfaction):
            satisfaction_value = ""
        else:
            satisfaction_value = int(satisfaction)

        customer_id = row.get("customer_id")
        customer_value = "" if pd.isna(customer_id) else str(customer_id).strip()

        rows.append(
            {
                "incident_id": row["incident_id"],
                "date": row["date"],
                "location_id": location_id,
                "category": category,
                "description": translate_description(str(row.get("description", ""))),
                "status": status,
                "customer_id": customer_value,
                "satisfaction_score": satisfaction_value,
                "reporter_id": row["reporter_id"],
            }
        )

    pd.DataFrame(rows).to_csv(OUTPUT, index=False)
    print(f"Wrote {OUTPUT} ({len(rows)} rows)")


if __name__ == "__main__":
    build()
