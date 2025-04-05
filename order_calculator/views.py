"""Django views for the Order Calculator plugin."""

import json
import logging

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt # Use carefully if needed, or handle CSRF properly

# Placeholder for the actual calculation logic module
# from .logic import calculate_required_components

log = logging.getLogger('inventree')


def calculator_view(request):
    """Render the main calculator page template."""
    context = {
        'plugin_title': 'BOM Order Calculator',
        # Add any other context needed for the template rendering
    }
    # Ensure the template path matches the directory structure
    return render(request, 'order_calculator/calculator_page.html', context)


# Use csrf_exempt carefully for API endpoints called via AJAX,
# or implement proper CSRF token handling in the frontend JS
@csrf_exempt
@require_POST # Ensure this view only accepts POST requests
def calculate_api_view(request):
    """API endpoint to handle the calculation request."""
    try:
        data = json.loads(request.body)
        targets = data.get('targets', []) # Expecting list like [{'part_id': 1110, 'quantity': 2}, ...]

        log.info(f"Received calculation request for targets: {targets}")

        if not targets:
            log.warning("Calculation request received with no targets.")
            return JsonResponse({'error': 'No target parts provided'}, status=400)

        # Convert targets to the format expected by the logic function
        # Ensure part_id is int and quantity is float
        target_dict = {}
        for item in targets:
            try:
                part_id = int(item.get('part_id'))
                quantity = float(item.get('quantity'))
                if quantity > 0:
                    target_dict[part_id] = quantity
                else:
                    log.warning(f"Ignoring target with non-positive quantity: {item}")
            except (ValueError, TypeError, KeyError):
                log.warning(f"Ignoring invalid target item: {item}")
                continue # Skip invalid items

        if not target_dict:
             log.warning("No valid targets found after parsing.")
             return JsonResponse({'error': 'No valid target parts provided'}, status=400)

        # --- Placeholder for calling the actual logic ---
        # Replace this with the actual call to your calculation function
        # from .logic import calculate_required_components
        # results = calculate_required_components(target_dict)
        log.info(f"Simulating calculation for: {target_dict}")
        # Example dummy result structure:
        results = [
             {'pk': 1055, 'name': 'Placeholder Component A', 'required': 7.0, 'in_stock': 1.0, 'to_order': 6.0},
             {'pk': 1455, 'name': 'Placeholder Component B', 'required': 0.5, 'in_stock': 0.0, 'to_order': 0.5},
        ]
        # --- End Placeholder ---

        log.info(f"Calculation successful. Returning {len(results)} items to order.")
        return JsonResponse({'success': True, 'results': results})

    except json.JSONDecodeError:
        log.error("Invalid JSON received in calculation request.")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        log.exception(f"Error during order calculation: {e}") # Log the full traceback
        return JsonResponse({'error': f'Calculation failed: {str(e)}'}, status=500)
