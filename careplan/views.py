import json
import anthropic
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
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

    print(">>> [1] Request received, method =", request.method)

    if request.method == "GET":
        print(">>> [2] GET request — returning empty form")
        return render(request, "form.html")

    # POST — collect form data, call LLM, store result, redirect to result page
    print(">>> [3] POST request — reading form data")
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

    print(">>> [4] Form data parsed:", order)
    print(">>> [5] Calling LLM — this will block for ~15-30 seconds...")
    

    order["care_plan"] = generate_care_plan(order)

    print(">>> [6] LLM responded — first 100 chars:", order["care_plan"][:100])

    order_id = NEXT_ID
    ORDERS[order_id] = order
    NEXT_ID += 1

    print(f">>> [7] Saved to memory — order_id = {order_id}, total orders in store: {len(ORDERS)}")
    print(f">>> [8] Redirecting to /result/{order_id}/")

    return redirect("order_result", order_id=order_id)


def order_result(request, order_id):
    print(f">>> [9] order_result view hit — order_id = {order_id}")

    order = ORDERS.get(order_id)
    if order is None:
        print(">>> [10] Order not found in memory — returning error page")
        return render(request, "form.html", {"error": "Order not found."})
    print(">>> [11] Order found — rendering result page")
    return render(request, "result.html", {
        "order": order,
        "order_id": order_id,
        "care_plan_raw": json.dumps(order["care_plan"]),
    })

# Search by name - personal practice
def search_orders_by_name(request):
    first_name = request.GET.get("first_name", "").strip()
    last_name = request.GET.get("last_name", "").strip()

    results = []

    for order_id, order in ORDERS.items():

        if not first_name and not last_name:
            continue
        if first_name and first_name.lower() not in order["first_name"].lower():
            continue
        if last_name and last_name.lower() not in order["last_name"].lower():
            continue

        results.append({
            "order_id": order_id,
            "first_name": order["first_name"],
            "last_name": order["last_name"],
            "mrn": order["mrn"],
            "medication_name": order["medication_name"],
        })
    
    return JsonResponse({"results": results})
