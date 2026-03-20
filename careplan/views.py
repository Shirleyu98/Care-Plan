import json
import anthropic
from django.conf import settings
from django.shortcuts import render, redirect

# ─── In-memory store ──────────────────────────────────────────────────────────
# This is intentionally the simplest possible storage.
# Every restart wipes the data. We will replace this with a DB later.
ORDERS = {}        # { order_id: { ...form fields, "care_plan": "..." } }
NEXT_ID = 1        # auto-increment counter


# ─── LLM call ─────────────────────────────────────────────────────────────────

def generate_care_plan(order: dict) -> str:
    """
    Calls the Anthropic API synchronously and returns the care plan as a string.
    The user's browser will hang until this returns (~10-30 seconds).
    This is the intentional tradeoff of the MVP — we'll fix it later with a queue.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""
You are a clinical pharmacist at a specialty pharmacy. Generate a structured care plan
for the following patient and order. Your output must contain exactly these four sections
with these exact headings:

## Problem List
## Goals
## Pharmacist Interventions
## Monitoring Plan

---

Patient: {order["first_name"]} {order["last_name"]}
MRN: {order["mrn"]}
Date of Birth: {order["dob"]}
Primary Diagnosis (ICD-10): {order["primary_diagnosis"]}
Additional Diagnoses: {order["additional_diagnoses"] or "None"}
Medication: {order["medication_name"]}
Medication History: {order["medication_history"] or "None"}
Referring Provider: {order["provider_name"]} (NPI: {order["provider_npi"]})

Patient Records / Clinical Notes:
{order["patient_records"]}

Write the care plan now.
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ─── Views ────────────────────────────────────────────────────────────────────

def order_form(request):
    global NEXT_ID

    if request.method == "GET":
        return render(request, "form.html")

    # POST — collect form data, call LLM, store result, redirect to result page
    order = {
        "first_name":           request.POST.get("first_name", "").strip(),
        "last_name":            request.POST.get("last_name", "").strip(),
        "mrn":                  request.POST.get("mrn", "").strip(),
        "dob":                  request.POST.get("dob", "").strip(),
        "provider_name":        request.POST.get("provider_name", "").strip(),
        "provider_npi":         request.POST.get("provider_npi", "").strip(),
        "primary_diagnosis":    request.POST.get("primary_diagnosis", "").strip(),
        "medication_name":      request.POST.get("medication_name", "").strip(),
        "additional_diagnoses": request.POST.get("additional_diagnoses", "").strip(),
        "medication_history":   request.POST.get("medication_history", "").strip(),
        "patient_records":      request.POST.get("patient_records", "").strip(),
    }

    order["care_plan"] = generate_care_plan(order)

    order_id = NEXT_ID
    ORDERS[order_id] = order
    NEXT_ID += 1

    return redirect("order_result", order_id=order_id)


def order_result(request, order_id):
    order = ORDERS.get(order_id)
    if order is None:
        return render(request, "form.html", {"error": "Order not found."})
    return render(request, "result.html", {
        "order": order,
        "order_id": order_id,
        "care_plan_raw": json.dumps(order["care_plan"]),
    })