from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

import json
from django.http import JsonResponse
from django.contrib.auth import authenticate, login

def landing(request):
    return render(request, "hospital/landing.html")

def login_view(request):

    if request.method == "POST":

        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.role == "viewer":
                redirect_url = "/viewer/dashboard/"
            elif user.role == "operator":
                redirect_url = "/operator/dashboard/"
            else:
                redirect_url = "/"

            return JsonResponse({
                "success": True,
                "redirect_url": redirect_url
            })

        return JsonResponse({
            "success": False,
            "error": "Invalid credentials"
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

def logout_view(request):
    logout(request)
    return redirect("landing")

@login_required
def viewer_dashboard(request):

    if request.user.role == "operator":
        return redirect("operator_dashboard")
    
    data={
        "hospital_name": request.user.hospital.name if request.user.hospital else "N/A",
    }
    return render(request, "hospital/viewer_dashboard.html", data)

def patients_list(request):
    return render(request, "hospital/patients_list.html")

@login_required
def operator_dashboard(request):

    if request.user.role == "viewer":
        return redirect("viewer_dashboard")
    
    return render(request, "hospital/operator_dashboard.html")