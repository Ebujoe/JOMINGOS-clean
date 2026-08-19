from django.shortcuts import render
from .genetic_scheduler import run_genetic_algorithm


def scheduler_dashboard(request):
    result = None

    if request.method == "POST":
        result = run_genetic_algorithm()

    return render(
        request,
        "scheduler/dashboard.html",
        {
            "result": result
        }
    )