from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from recipes.models import Ingredient


class ShoppingListItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shopping_list"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity_needed = models.DecimalField(max_digits=8, decimal_places=2,  validators=[MinValueValidator(0.01, message="Quantity must be greater than zero.")],)
    is_purchased = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "ingredient", "is_purchased")

    def __str__(self):
        return f"{self.user.username} needs {self.quantity_needed} {self.ingredient.unit} of {self.ingredient.title}"
