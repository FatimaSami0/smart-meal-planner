from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from pantry.models import PantryItem
from recipes.models import Recipe

from .forms import ShoppingListItemForm, ShoppingListQuantityForm
from .models import ShoppingListItem


def _notify_item_saved(request, item, created):
    """Sends a standardized success message for added or updated items."""
    if created:
        messages.success(
            request,
            f'"{item.ingredient.title}" added to your shopping list!',
        )
    else:
        messages.success(
            request,
            f'Updated "{item.ingredient.title}" — now '
            f"{item.quantity_needed} {item.ingredient.unit}.",
        )


def _add_or_update_item(user, ingredient, quantity_needed):
    """
    Adds quantity to an existing ACTIVE item,
    or creates a brand new one.
    Leaves purchased items untouched.
    """
    item = ShoppingListItem.objects.filter(
        user=user,
        ingredient=ingredient,
        is_purchased=False,
    ).first()

    if item:
        item.quantity_needed += quantity_needed
        item.full_clean()
        item.save()
        created = False
    else:
        item = ShoppingListItem.objects.create(
            user=user,
            ingredient=ingredient,
            quantity_needed=quantity_needed,
            is_purchased=False,
        )
        created = True

    return item, created


@login_required
@require_http_methods(["GET"])
def shopping_list(request):
    items = (
        ShoppingListItem.objects.filter(user=request.user)
        .select_related("ingredient")
    )

    return render(
        request,
        "shopping_list/shopping_list.html",
        {
            "items": items,
            "form": ShoppingListItemForm(),
        },
    )


@login_required
@require_POST
def add_item(request):
    """
    Handles both ways of adding items:
    1. From the shopping list page.
    2. From the recipe page.
    """
    form = ShoppingListItemForm(request.POST)

    if form.is_valid():
        ingredient = form.cleaned_data["ingredient"]
        quantity_needed = form.cleaned_data["quantity_needed"]

        item, created = _add_or_update_item(
            request.user,
            ingredient,
            quantity_needed,
        )

        _notify_item_saved(request, item, created)

    else:
        messages.error(request, "Please fix the errors below.")

    recipe_id = request.POST.get("recipe_id")

    if recipe_id:
        return redirect(
            "recipes:recipe_detail",
            recipe_id=recipe_id,
        )

    return redirect("shopping_list:shopping_list")


@login_required
@require_POST
def edit_item(request, item_id):
    item = get_object_or_404(
        ShoppingListItem,
        id=item_id,
        user=request.user,
    )

    form = ShoppingListQuantityForm(
        request.POST,
        instance=item,
    )

    if form.is_valid():
        form.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "quantity_needed": f"{item.quantity_needed:g}",
                }
            )

        messages.success(
            request,
            f'Updated "{item.ingredient.title}".',
        )

    elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )

    return redirect("shopping_list:shopping_list")


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_item(request, item_id):
    item = get_object_or_404(
        ShoppingListItem,
        id=item_id,
        user=request.user,
    )

    item.delete()
    messages.info(request, "Item removed from your shopping list.")

    return redirect("shopping_list:shopping_list")


@login_required
@require_POST
def clear_shopping_list(request):
    ShoppingListItem.objects.filter(
        user=request.user,
    ).delete()

    return redirect("shopping_list:shopping_list")


@login_required
@require_POST
def clear_purchased_items(request):
    deleted_count, _ = ShoppingListItem.objects.filter(
        user=request.user,
        is_purchased=True,
    ).delete()

    if deleted_count > 0:
        messages.success(
            request,
            f"Cleared {deleted_count} purchased item(s)!",
        )
    else:
        messages.info(
            request,
            "No purchased items to clear.",
        )

    return redirect("shopping_list:shopping_list")


@login_required
@require_POST
def toggle_purchased(request, item_id):
    item = get_object_or_404(
        ShoppingListItem,
        id=item_id,
        user=request.user,
    )

    target_status = not item.is_purchased

    if target_status:
        pantry_item, created = PantryItem.objects.get_or_create(
            user=request.user,
            ingredient=item.ingredient,
            defaults={
                "quantity": item.quantity_needed,
            },
        )

        if not created:
            pantry_item.quantity += item.quantity_needed
            pantry_item.save()

        messages.success(
            request,
            f"Added {item.quantity_needed} "
            f"{item.ingredient.title} to your pantry!",
        )

    existing_target_item = (
        ShoppingListItem.objects.filter(
            user=request.user,
            ingredient=item.ingredient,
            is_purchased=target_status,
        )
        .exclude(id=item.id)
        .first()
    )

    if existing_target_item:
        existing_target_item.quantity_needed += item.quantity_needed
        existing_target_item.save()
        item.delete()
    else:
        item.is_purchased = target_status
        item.save()

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "shopping_list:shopping_list",
        )
    )


@login_required
@require_POST
def add_all_missing(request, recipe_id):
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related(
            "recipeingredient_set__ingredient"
        ),
        id=recipe_id,
    )

    pantry = {
        item.ingredient_id: item.quantity
        for item in PantryItem.objects.filter(user=request.user)
    }

    added_count = 0

    for ri in recipe.recipeingredient_set.all():
        missing_qty = (
            ri.required_quantity
            - pantry.get(ri.ingredient_id, 0)
        )

        if missing_qty > 0:
            _add_or_update_item(
                request.user,
                ri.ingredient,
                missing_qty,
            )
            added_count += 1

    if added_count:
        messages.success(
            request,
            f"{added_count} missing ingredient(s) "
            "added to your shopping list!",
        )
    else:
        messages.info(
            request,
            "Nothing to add — you already have everything "
            "or it's all on your list.",
        )

    return redirect(
        "recipes:recipe_detail",
        recipe_id=recipe_id,
    )