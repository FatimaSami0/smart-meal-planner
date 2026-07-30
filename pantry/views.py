from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import PantryItemForm
from .models import PantryItem


@login_required
@require_http_methods(["GET"])
def pantry_list_view(request):
    # Get all pantry items for the current user (ingredient pre-joined)
    pantry_items = PantryItem.objects.select_related("ingredient").filter(
        user=request.user
    )

    form = PantryItemForm()

    context = {
        "pantry_items": pantry_items,
        "form": form,
    }
    return render(request, "pantry/pantry_list.html", context)


@login_required
@require_http_methods(["POST"])
def pantry_add_view(request):
    form = PantryItemForm(request.POST)

    # Return form errors if the submitted data is invalid
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(form.errors, status=400)

        pantry_items = PantryItem.objects.select_related("ingredient").filter(
            user=request.user
        )
        return render(
            request,
            "pantry/pantry_list.html",
            {"pantry_items": pantry_items, "form": form},
        )

    ingredient = form.cleaned_data["ingredient"]
    quantity = form.cleaned_data["quantity"]
    expiration_date = form.cleaned_data.get("expiration_date")

    #Add select_related so ingredient title/unit are preloaded for JSON
    existing_item = (
        PantryItem.objects.select_related("ingredient")
        .filter(
            user=request.user, ingredient=ingredient, expiration_date=expiration_date
        )
        .first()
    )

    if existing_item:
        existing_item.quantity += quantity
        existing_item.save(update_fields=["quantity"])
        item = existing_item
        message = "Matching ingredient batch found. Quantity updated successfully!"
    else:
        # Otherwise, create a new pantry item
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        message = "Item saved successfully."

    # Return JSON response for AJAX requests
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = {
            "id": item.id,
            "ingredient_name": item.ingredient.title,
            "quantity": item.quantity,
            "unit": item.ingredient.unit,
            "expiration_date": item.expiration_date.strftime("%Y-%m-%d") if item.expiration_date else "",
            "message": message,
        }
        return JsonResponse(data, status=200)

    messages.success(request, message)
    return redirect("pantry:list")


@login_required
@require_http_methods(["GET", "POST"])
def pantry_update_view(request, pk):
    # select_related to avoid N+1 queries when rendering the confirmation template
    item = get_object_or_404(
        PantryItem.objects.select_related("ingredient"), pk=pk, user=request.user
    )

    data = request.POST.copy()

    # keep the current ingredient if it wasn't submitted
    if "ingredient" not in data:
        data["ingredient"] = item.ingredient_id

    form = PantryItemForm(data, instance=item)

    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        return redirect("pantry:list")

    # save the updated pantry item
    item = form.save()
    message = "Item updated successfully."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "id": item.id,
            "ingredient_name": item.ingredient.title,
            "quantity": item.quantity,
            "unit": item.ingredient.unit,
            "message": message,
        }, status=200)

    return redirect("pantry:list")


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def pantry_delete_view(request, pk):
    # OPTIMIZED: Preload ingredient for confirmation template rendering
    item = get_object_or_404(
        PantryItem.objects.select_related("ingredient"), pk=pk, user=request.user
    )

    # Show a confirmation page before deleting
    if request.method == "GET":
        return render(request, "pantry/pantry_confirm_delete.html", {"object": item})

    item.delete()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": "Item deleted successfully."}, status=200)

    return redirect("pantry:list")


@login_required
@require_http_methods(["POST", "DELETE"])
def clear_pantry(request):
    # Remove all pantry items for the current user
    PantryItem.objects.filter(
        user=request.user
    ).delete()

    return redirect("pantry:list")
