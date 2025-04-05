"""URL definitions for the Order Calculator plugin."""

from django.urls import path

from . import views

# Define URL patterns for the plugin app
urlpatterns = [
    # URL for the main calculator page view
    path('', views.calculator_view, name='calculator-page'),

    # URL for the backend API endpoint that performs the calculation
    path('calculate/', views.calculate_api_view, name='calculate-api'),
]
