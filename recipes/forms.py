from django import forms
from .models import Recipe


class RecipeSearchFilterForm(forms.Form):
    # Search box for recipe names
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search recipes by name...",
            }
        ),
    )

    # dropdown to filter recipes by meal type
    meal_type = forms.ChoiceField(
        choices=[("", "All Meal Types")] + Recipe.MealTypeChoices.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Filter recipes by category
    category = forms.ChoiceField(
        choices=[("", "All Categories")] + Recipe.RecipeCategoryChoices.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )