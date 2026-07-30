from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from pantry.models import PantryItem
from shopping_list.models import ShoppingListItem

from .forms import RecipeSearchFilterForm
from .models import FavoriteRecipe, Ingredient, Recipe

# Number of recipes shown per page(constant for all pages)
PAGINATE_BY = 9


def get_pantry_quantities(user):
    # Get the total quantity of each ingredient in the user's pantry
    pantry_totals = (
        PantryItem.objects.filter(user=user)
        .values("ingredient_id")
        .annotate(total_quantity=Sum("quantity"))
    )
    return {item["ingredient_id"]: item["total_quantity"] for item in pantry_totals}


def _filter_recipes(request):
    # Apply search/filter options with prefetching to fix N+1 queries across list & live search
    form = RecipeSearchFilterForm(request.GET)
    recipes = Recipe.objects.prefetch_related("recipeingredient_set__ingredient")

    if form.is_valid():
        search_query = form.cleaned_data.get("search_query")
        meal_type = form.cleaned_data.get("meal_type")
        category = form.cleaned_data.get("category")

        if search_query:
            recipes = recipes.filter(title__icontains=search_query)
        if meal_type:
            recipes = recipes.filter(meal_type=meal_type)
        if category:
            recipes = recipes.filter(category=category)

    return recipes.order_by("title"), form


@require_GET
def recipe_list(request):
    recipes, form = _filter_recipes(request)

    # Split recipes into pages
    paginator = Paginator(recipes, PAGINATE_BY)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "recipes/recipe_list.html",
        {
            "recipes": page_obj,
            "page_obj": page_obj,
            "form": form,
        },
    )


@login_required
@require_GET
def recipe_detail(request, recipe_id):
    # Get the selected recipe with all its ingredients
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related("recipeingredient_set__ingredient"),
        id=recipe_id,
    )

    pantry_quantities = get_pantry_quantities(request.user)

    # ingredients already added to the shopping list
    shopping_quantities = {
        item.ingredient_id: item.quantity_needed
        for item in ShoppingListItem.objects.filter(user=request.user)
    }

    ingredients_with_status = []

    # Check each ingredient and compare it with the pantry
    for ri in recipe.recipeingredient_set.all():
        available_qty = pantry_quantities.get(ri.ingredient.id, 0)
        has_enough = available_qty >= ri.required_quantity
        missing_qty = max(ri.required_quantity - available_qty, 0)
        shopping_qty = shopping_quantities.get(ri.ingredient.id, 0)

        # check if the shopping list already covers the missing quantity
        covers_shortfall = missing_qty > 0 and shopping_qty >= missing_qty

        ingredients_with_status.append(
            {
                "ri": ri,
                "has_enough": has_enough,
                "available_qty": available_qty,
                "missing_qty": missing_qty,
                "shopping_qty": shopping_qty,
                "covers_shortfall": covers_shortfall,
            }
        )

    # True if everything is available or already added to shopping list
    all_missing_added = all(
        item["has_enough"] or item["covers_shortfall"]
        for item in ingredients_with_status
    )

    # Check if this recipe is in the user's favorites
    is_favorite = FavoriteRecipe.objects.filter(
        user=request.user, recipe=recipe
    ).exists()

    return render(
        request,
        "recipes/recipe_detail.html",
        {
            "recipe": recipe,
            "ingredients_with_status": ingredients_with_status,
            "all_missing_added": all_missing_added,
            "is_favorite": is_favorite,
        },
    )


@login_required
@require_GET
def recommended_recipes(request):
    # Get all ingredients available in the pantry
    pantry_ingredient_ids = set(
        PantryItem.objects.filter(user=request.user).values_list(
            "ingredient_id", flat=True
        )
    )

    if not pantry_ingredient_ids:
        return render(
            request,
            "recipes/recommended.html",
            {"scored_recipes": []},
        )

    # Get all recipes that use at least one of the ingredients in the pantry
    all_recipes = (
        Recipe.objects.filter(recipeingredient__ingredient_id__in=pantry_ingredient_ids)
        .distinct()
        .prefetch_related("recipeingredient_set__ingredient")
    )
    scored_recipes = []

    # Calculate how well each recipe matches the pantry
    for recipe in all_recipes:
        recipe_ingredients = recipe.recipeingredient_set.all()

        total_needed = len(recipe_ingredients)
        matched = sum(
            1 for ri in recipe_ingredients if ri.ingredient.id in pantry_ingredient_ids
        )

        if matched > 0:
            match_percent = round(matched / total_needed * 100) if total_needed else 0

            scored_recipes.append(
                {
                    "recipe": recipe,
                    "matched": matched,
                    "total": total_needed,
                    "match_percent": match_percent,
                    "can_cook": total_needed > 0 and matched == total_needed,
                }
            )

    # Show the best matching recipes first
    scored_recipes.sort(key=lambda x: (x["match_percent"], x["matched"]), reverse=True)

    paginator = Paginator(scored_recipes, PAGINATE_BY)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "recipes/recommended.html",
        {
            "scored_recipes": page_obj,
            "page_obj": page_obj,
        },
    )


@require_GET
def live_search(request):
    # Return filtered recipes while the user is typing
    recipes, _ = _filter_recipes(request)

    return render(
        request,
        "recipes/_recipe_results.html",
        {"recipes": recipes[:20]},
    )


@login_required
def toggle_favorite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)

    # Add or remove the recipe from favorites
    favorite = FavoriteRecipe.objects.filter(
        user=request.user,
        recipe=recipe,
    )

    if favorite.exists():
        favorite.delete()
    else:
        FavoriteRecipe.objects.create(
            user=request.user,
            recipe=recipe,
        )

    return redirect(
        "recipes:recipe_detail",
        recipe_id=recipe.id,
    )


@login_required
@require_GET
def favorite_recipes(request):
    # Get all favorite recipes for the logged-in user with prefetching to avoid N+1 queries
    favorites = (
        FavoriteRecipe.objects.filter(user=request.user)
        .select_related("recipe")
        .prefetch_related("recipe__recipeingredient_set__ingredient")
        .order_by("recipe__title")
    )

    paginator = Paginator(favorites, PAGINATE_BY)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "recipes/favorites.html",
        {
            "favorites": page_obj,
            "page_obj": page_obj,
        },
    )


@login_required
@require_POST
def remove_favorite(request, recipe_id):
    # Remove one recipe from favorites
    FavoriteRecipe.objects.filter(
        user=request.user,
        recipe_id=recipe_id,
    ).delete()

    return redirect("recipes:favorite_recipes")


@login_required
@require_POST
def clear_favorites(request):
    # delete all favorite recipes
    FavoriteRecipe.objects.filter(user=request.user).delete()

    return redirect("recipes:favorite_recipes")


@login_required
@require_GET
def ingredient_search(request):
    query = request.GET.get("q", "").strip()

    # Don't search if the input is empty
    if len(query) < 1:
        return JsonResponse({"results": []})

    ingredients = Ingredient.objects.filter(title__icontains=query).order_by("title")

    # Return matching ingredients as JSON
    results = [
        {"id": ing.id, "title": ing.title, "unit": ing.unit} for ing in ingredients
    ]
    return JsonResponse({"results": results})