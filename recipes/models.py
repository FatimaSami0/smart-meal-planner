from django.db import models
from django.conf import settings


class Ingredient(models.Model):
    # Categories for ingredients
    class CategoryChoices(models.TextChoices):
        VEGETABLES = "vegetables", "Vegetables"
        FRUITS = "fruits", "Fruits"
        MEAT = "meat", "Meat"
        DAIRY = "dairy", "Dairy"
        SPICES = "spices", "Spices"
        GRAINS = "grains", "Grains"
        OTHER = "other", "Other"

    # Units used to measure ingredients
    class QuantityUnitChoices(models.TextChoices):
        GRAM = "g", "Grams"
        KILOGRAM = "kg", "Kilograms"
        MILLILITER = "ml", "Milliliters"
        LITER = "l", "Liters"
        TEASPOON = "tsp", "Teaspoon"
        PIECE = "pcs", "Pieces"
        OTHER = "other", "Other"

    title = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.OTHER,
    )
    unit = models.CharField(
        max_length=50,
        choices=QuantityUnitChoices.choices,
        default=QuantityUnitChoices.OTHER,
    )

    # Show the ingredient name instead of the object id
    def __str__(self):
        return self.title


class Recipe(models.Model):
    # Available meal types
    class MealTypeChoices(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    # Recipe categories
    class RecipeCategoryChoices(models.TextChoices):
        DESSERT = "dessert", "Dessert"
        PASTRIES = "pastries", "Pastries"
        GRILLS = "grills", "Grills"
        SOUPS = "soups", "Soups"
        SALADS = "salads", "Salads"
        MAIN_DISH = "main_dish", "Main Dish"

    title = models.CharField(max_length=200, unique=True)

    # Steps to prepare the recipe
    instructions = models.TextField(
        help_text="instructions of preparation", null=True, blank=True
    )

    prep_time = models.PositiveIntegerField(null=True, blank=True)

    meal_type = models.CharField(
        max_length=50,
        choices=MealTypeChoices.choices,
        null=True,
        blank=True,
    )

    category = models.CharField(
        max_length=50,
        choices=RecipeCategoryChoices.choices,
        null=True,
        blank=True,
    )

    image_url = models.URLField(blank=True)

    # Connect recipes with ingredients through RecipeIngredient
    ingredients = models.ManyToManyField(Ingredient, through="RecipeIngredient")

    # Bootstrap icon for each recipe category
    CATEGORY_ICONS = {
        RecipeCategoryChoices.DESSERT: "bi-cake2-fill",
        RecipeCategoryChoices.PASTRIES: "bi-cookie",
        RecipeCategoryChoices.GRILLS: "bi-fire",
        RecipeCategoryChoices.SOUPS: "bi-cup-hot-fill",
        RecipeCategoryChoices.SALADS: "bi-flower3",
        RecipeCategoryChoices.MAIN_DISH: "bi-egg-fried",
    }

    # return the matching icon, otherwise use the default one
    @property
    def icon(self):
        return self.CATEGORY_ICONS.get(self.category, "bi-basket2")

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    # Links each recipe with its ingredients and quantity
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    required_quantity = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        # dont allow the same ingredient to be added twice to one recipe
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            )
        ]

    def __str__(self):
        return f"{self.required_quantity} {self.ingredient.unit} of {self.ingredient.title} for {self.recipe.title}"


# Stores the recipes a user marked as favorite
class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
    )

    class Meta:
        # prevent adding the same recipe to favorites more than once
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_user_favorite_recipe",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.recipe}"