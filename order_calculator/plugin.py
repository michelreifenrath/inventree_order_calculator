"""Plugin definition for the Order Calculator."""

from plugin import InvenTreePlugin
from plugin.mixins import AppMixin, UrlsMixin

# Import the urls module for this plugin
try:
    import order_calculator.urls as MyUrls
except Exception:
    # Fallback if the urls module cannot be imported
    # TODO: Add logging here
    MyUrls = None


class OrderCalculatorPlugin(AppMixin, UrlsMixin, InvenTreePlugin):
    """A plugin for calculating required components based on BOMs."""

    NAME = "Order Calculator"
    SLUG = "ordercalculator"
    TITLE = "BOM Order Calculator"
    DESCRIPTION = "Calculates required components based on selected assemblies and quantities."
    VERSION = "0.1.0"
    AUTHOR = "Cline (AI Assistant)" # Or your name/org

    # Provide URL namespace and patterns
    URL_NAMESPACE = "order-calculator"
    URL_PATTERNS = []

    # Add custom URLs if MyUrls was imported successfully
    if MyUrls:
        URL_PATTERNS.append(MyUrls)

    # Settings for AppMixin to add an entry to the navigation sidebar
    NAVIGATION_ENABLED = True
    NAVIGATION_TAB_NAME = "Calculate Orders"
    NAVIGATION_TAB_ICON = "fas fa-calculator"

    # Add any custom settings for the plugin here if needed later
    # SETTINGS = { ... }

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        # Initialization code here if needed
