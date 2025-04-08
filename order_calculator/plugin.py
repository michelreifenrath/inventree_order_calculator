"""Plugin definition for the Order Calculator."""

from plugin import InvenTreePlugin
from plugin.mixins import UserInterfaceMixin, UrlsMixin

# Import the urls module for this plugin
try:
    import order_calculator.urls as MyUrls
except Exception:
    # Fallback if the urls module cannot be imported
    # TODO: Add logging here
    MyUrls = None


class OrderCalculatorPlugin(UserInterfaceMixin, UrlsMixin, InvenTreePlugin):
    """A plugin for calculating required components based on BOMs."""

    NAME = "Order Calculator"
    SLUG = "ordercalculator"
    TITLE = "BOM Order Calculator"
    DESCRIPTION = "Calculates required components based on selected assemblies and quantities."
    VERSION = "0.1.1"
    AUTHOR = "Cline (AI Assistant)" # Or your name/org

    # Provide URL namespace and patterns
    URL_NAMESPACE = "order-calculator"
    URL_PATTERNS = []

    # Add custom URLs if MyUrls was imported successfully
    if MyUrls:
        URL_PATTERNS.append(MyUrls)

    # Note: Navigation via AppMixin is removed, using UserInterfaceMixin for dashboard widget

    # Add any custom settings for the plugin here if needed later
    # SETTINGS = { ... }

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        # Initialization code here if needed

    def get_ui_panels(self, request, context=None, **kwargs):
        """Register UI panels for this plugin. (Not used for dashboard widgets)."""
        return [] # Dashboard widgets are handled by get_ui_dashboard_items

    def get_ui_dashboard_items(self, request, context=None, **kwargs):
        """Register dashboard items (widgets) for this plugin."""
        widgets = []

        # Note: No need to check view context here, this method is specifically for dashboard items.
        widgets.append({
            'key': 'order-calculator-widget',
            'title': 'BOM Order Calculator',
            'description': 'Calculate required components',
            'icon': 'fas fa-calculator',
            'feature_type': 'dashboard_widget', # Specify this is a dashboard widget
            'source': self.plugin_static_file(
                'OrderCalculatorWidget.js:renderWidget' # Points to our JS file/function
            ),
            'context': {
                # Pass any initial context needed by the React component
                'apiUrl': '/order-calculator/calculate/', # Pass API URL to frontend
            }
        })

        return widgets
