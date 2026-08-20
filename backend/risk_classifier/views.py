from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from patients.models import Patient
from vitals.models import VitalSigns
from ml_model.predict import predict_risk

GENDER_MAP = {"M": "Male", "F": "Female", "O": "Male"}


@login_required
@require_http_methods(["GET"])
def get_ml_risk_prediction(request, patient_id):

    patient = get_object_or_404(Patient, pk=patient_id)

    latest_vital = VitalSigns.objects.filter(patient=patient).order_by("-recorded_at").first()
    if latest_vital is None:
        return JsonResponse({"error": "This patient has no recorded vitals yet."}, status=400)

    required_raw_fields = {
        "Heart Rate (bpm)": latest_vital.heart_rate,
        "Resp Rate (bpm)": latest_vital.respiratory_rate,
        "Body Temp (C)": latest_vital.temperature,
        "SpO2 (%)": latest_vital.oxygen_saturation,
        "Systolic BP (mmHg)": latest_vital.bp_systolic,
        "Diastolic BP (mmHg)": latest_vital.bp_diastolic,
    }
    missing = [name for name, value in required_raw_fields.items() if value is None]
    if missing:
        return JsonResponse({
            "error": "This patient's latest vitals record is missing required fields.",
            "missing_fields": missing,
        }, status=400)

    vitals = {
        "Age": patient.get_age(),
        "Gender": GENDER_MAP.get(patient.gender, "Male"),
        "Heart Rate (bpm)": float(latest_vital.heart_rate),
        "Resp Rate (bpm)": float(latest_vital.respiratory_rate),
        "Body Temp (C)": float(latest_vital.temperature),
        "SpO2 (%)": float(latest_vital.oxygen_saturation),
        "Systolic BP (mmHg)": float(latest_vital.bp_systolic),
        "Diastolic BP (mmHg)": float(latest_vital.bp_diastolic),
        "On Oxygen": "No",
        "Consciousness": "Alert",
    }

    try:
        result = predict_risk(vitals)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({
        "success": True,
        "patient": {
            "id": patient.id,
            "name": patient.get_full_name(),
        },
        "based_on_vital_recorded_at": latest_vital.recorded_at.isoformat(),
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "reasons": result["reasons"],
        "borderline": result["borderline"],
        "note": "Consciousness and On Oxygen were not available in this patient's record and were defaulted to 'Alert' and 'No'.",
    })


@login_required
@require_http_methods(["GET", "POST"])
def vitals_check_view(request):
    result = None
    error = None
    submitted = {}

    if request.method == "POST":
        submitted = {
            "age": request.POST.get("age", ""),
            "gender": request.POST.get("gender", ""),
            "heart_rate": request.POST.get("heart_rate", ""),
            "resp_rate": request.POST.get("resp_rate", ""),
            "body_temp": request.POST.get("body_temp", ""),
            "spo2": request.POST.get("spo2", ""),
            "systolic_bp": request.POST.get("systolic_bp", ""),
            "diastolic_bp": request.POST.get("diastolic_bp", ""),
            "on_oxygen": request.POST.get("on_oxygen", ""),
            "consciousness": request.POST.get("consciousness", ""),
        }

        try:
            vitals = {
                "Age": float(submitted["age"]),
                "Gender": submitted["gender"],
                "Heart Rate (bpm)": float(submitted["heart_rate"]),
                "Resp Rate (bpm)": float(submitted["resp_rate"]),
                "Body Temp (C)": float(submitted["body_temp"]),
                "SpO2 (%)": float(submitted["spo2"]),
                "Systolic BP (mmHg)": float(submitted["systolic_bp"]),
                "Diastolic BP (mmHg)": float(submitted["diastolic_bp"]),
                "On Oxygen": submitted["on_oxygen"],
                "Consciousness": submitted["consciousness"],
            }
            result = predict_risk(vitals)
        except (ValueError, TypeError):
            error = "Please check your inputs -- one or more fields are missing or not a valid number."

    return render(request, "risk_classifier/vitals_check.html", {
        "result": result,
        "error": error,
        "submitted": submitted,
    })