"""Core calculation logic for the Order Calculator plugin."""

import logging
from collections import defaultdict
from decimal import Decimal

# Import necessary InvenTree models
from part.models import Part, BomItem
from stock.models import StockItem
from InvenTree.status_codes import StockStatusGroups # Correct import path

# Import Django ORM tools
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce

log = logging.getLogger('inventree')

# --- Caches (request-scoped) ---
# These will be populated during a single calculation request
part_cache = {} # {part_id: {'assembly': bool, 'name': str, 'in_stock': Decimal}}
bom_cache = {} # {part_id: list_of_bom_item_dicts}

# --- ORM Implementation Functions ---

def get_part_details_orm(part_id: int) -> dict | None:
    """Gets part details (assembly, name, stock) using ORM."""
    try:
        # Fetch the part object
        part = Part.objects.get(pk=part_id)

        # Calculate available stock using aggregation and IN_STOCK_FILTER
        # Note: StockItem.IN_STOCK_FILTER already includes quantity > 0 and status checks
        stock_info = StockItem.objects.filter(
            StockItem.IN_STOCK_FILTER,
            part=part
        ).aggregate(
            total_stock=Coalesce(Sum('quantity'), Decimal(0), output_field=DecimalField())
        )

        details = {
            'assembly': part.assembly,
            'name': part.name,
            'in_stock': stock_info['total_stock']
        }
        log.debug(f"ORM: Fetched details for part {part_id}: {details}")
        return details
    except Part.DoesNotExist:
        log.warning(f"Part ID {part_id} not found in database.")
        return None
    except Exception as e:
        log.error(f"Error fetching ORM part details for ID {part_id}: {e}", exc_info=True)
        return None


def get_bom_items_orm(part_id: int) -> list | None:
    """Gets BOM items for a part ID using ORM."""
    try:
        # Fetch BOM items for the given part_id
        # Use select_related('sub_part') to potentially optimize if sub_part details are needed later,
        # although caching might handle this. It doesn't hurt much to include it.
        bom_items_raw = BomItem.objects.filter(part_id=part_id).select_related('sub_part')

        # Extract only the necessary information
        bom_data = [{'sub_part': item.sub_part_id, 'quantity': float(item.quantity)} for item in bom_items_raw]
        log.debug(f"ORM: Fetched {len(bom_data)} BOM items for part {part_id}")
        return bom_data
    except Exception as e:
        log.error(f"Error fetching ORM BOM items for part ID {part_id}: {e}", exc_info=True)
        return None


def get_final_part_data_orm(part_ids: list[int]) -> dict[int, dict]:
    """Fetches final data (name, stock) for multiple part IDs using ORM."""
    final_data = {}
    if not part_ids:
        return final_data

    log.info(f"ORM: Fetching final details (name, stock) for {len(part_ids)} base components...")
    try:
        # Efficiently fetch parts and annotate available stock count
        # The filter=Q(...) within Sum is crucial for applying the IN_STOCK_FILTER correctly
        parts = Part.objects.filter(pk__in=part_ids).annotate(
            available_stock=Coalesce(
                Sum('stock_items__quantity', filter=StockItem.IN_STOCK_FILTER),
                Decimal(0),
                output_field=DecimalField()
            )
        ).values('pk', 'name', 'available_stock') # Use .values() for efficiency

        for part_data in parts:
            final_data[part_data['pk']] = {
                'name': part_data['name'],
                'in_stock': part_data['available_stock']
            }

        log.info(f"ORM: Successfully fetched batch details for {len(final_data)} parts.")

        # Add entries for any parts requested but not found in the batch query
        # (e.g., if a part ID was invalid or had no stock items at all,
        # though the query should ideally handle zero stock via Coalesce)
        missed_ids = set(part_ids) - set(final_data.keys())
        if missed_ids:
            log.warning(f"ORM: Could not fetch batch details for some part IDs: {missed_ids}. Fetching names individually.")
            # Fetch names individually for missing parts
            missing_parts = Part.objects.filter(pk__in=missed_ids).values('pk', 'name')
            missing_names = {p['pk']: p['name'] for p in missing_parts}
            for missed_id in missed_ids:
                final_data[missed_id] = {
                    'name': missing_names.get(missed_id, f"Unknown (ID: {missed_id})"),
                    'in_stock': Decimal(0)
                }

    except Exception as e:
        log.error(f"Error fetching batch final part data ORM: {e}", exc_info=True)
        # Fallback: return unknowns for all requested IDs on major error
        for part_id in part_ids:
             final_data[part_id] = {'name': f"Unknown (ID: {part_id})", 'in_stock': Decimal(0)}

    log.info("ORM: Finished fetching final part data.")
    return final_data


# --- Calculation Logic (Adapted from script, using ORM placeholders) ---

def get_part_details_cached(part_id: int) -> dict | None:
    """Gets part details from cache or ORM."""
    if part_id in part_cache:
        log.debug(f"Cache hit for part details: {part_id}")
        return part_cache[part_id]

    log.debug(f"Cache miss for part details: {part_id}. Fetching from ORM.")
    details = get_part_details_orm(part_id)
    part_cache[part_id] = details # Cache result (even if None)
    return details

def get_bom_items_cached(part_id: int) -> list | None:
    """Gets BOM items for a part ID from cache or ORM."""
    if part_id in bom_cache:
        log.debug(f"Cache hit for BOM: {part_id}")
        return bom_cache[part_id]

    log.debug(f"Cache miss for BOM: {part_id}. Fetching from ORM.")
    # Need part details first to check if it's an assembly
    part_details = get_part_details_cached(part_id)
    if not part_details or not part_details['assembly']:
        log.debug(f"Part {part_id} is not an assembly or details failed. No BOM.")
        bom_cache[part_id] = [] # Cache empty list for non-assemblies
        return []

    bom_data = get_bom_items_orm(part_id)
    bom_cache[part_id] = bom_data # Cache result (even if None or [])
    return bom_data


def get_recursive_bom_cached(part_id: int, quantity: float, required_components: defaultdict[int, float]):
    """Recursively processes the BOM using cached data, aggregating required base components."""
    part_details = get_part_details_cached(part_id)
    if not part_details:
        log.warning(f"Skipping part ID {part_id} in recursive BOM due to fetch error.")
        return

    if part_details['assembly']:
        log.debug(f"Processing assembly: {part_details['name']} (ID: {part_id}), Quantity: {quantity}")
        bom_items = get_bom_items_cached(part_id)
        if bom_items: # Check if BOM fetch succeeded and is not empty
            for item in bom_items:
                sub_part_id = item['sub_part']
                sub_quantity_per = float(item['quantity']) # Ensure float
                total_sub_quantity = quantity * sub_quantity_per
                # Recursively process the sub-part
                get_recursive_bom_cached(sub_part_id, total_sub_quantity, required_components)
        elif bom_items is None: # BOM fetch failed
             log.warning(f"Could not process BOM for assembly {part_id} due to fetch error.")
        # If bom_items is [], it's an empty BOM, do nothing further for this branch
    else:
        # This is a base component
        log.debug(f"Adding base component: {part_details['name']} (ID: {part_id}), Quantity: {quantity}")
        required_components[part_id] += quantity


def calculate_required_components(target_assembly_ids: dict[int, float]) -> list[dict]:
    """
    Main function to calculate required components.
    Takes a dictionary of {part_id: quantity} for the top-level assemblies.
    Returns a list of dictionaries for parts to order.
    """
    log.info(f"Starting component calculation for targets: {target_assembly_ids}")

    required_base_components = defaultdict(float)
    # Clear caches at the start of each calculation run
    part_cache.clear()
    bom_cache.clear()

    log.info("Calculating required components recursively (with caching)...")
    for part_id, quantity in target_assembly_ids.items():
        log.info(f"Processing target assembly ID: {part_id}, Quantity: {quantity}")
        get_recursive_bom_cached(part_id, float(quantity), required_base_components)

    log.info(f"Total unique base components identified: {len(required_base_components)}")
    if not required_base_components:
        log.info("No base components found.")
        return []

    # Get Final Data (Names & Stock) for Base Components using ORM
    base_component_ids = list(required_base_components.keys())
    final_part_data = get_final_part_data_orm(base_component_ids)

    # Calculate Order List
    parts_to_order = []
    log.info("Calculating final order quantities...")
    for part_id, required_qty_float in required_base_components.items():
        required_qty = Decimal(str(required_qty_float)) # Use Decimal for precision
        part_data = final_part_data.get(part_id, {'name': f"Unknown (ID: {part_id})", 'in_stock': Decimal(0)})
        # Ensure in_stock is Decimal
        in_stock = Decimal(str(part_data.get('in_stock', 0)))
        part_name = part_data.get('name', f"Unknown (ID: {part_id})")

        to_order = required_qty - in_stock
        if to_order > 0:
            parts_to_order.append({
                "pk": part_id,
                "name": part_name,
                # Convert back to float for JSON serialization if needed, or keep Decimal
                "required": float(required_qty.quantize(Decimal("0.001"))),
                "in_stock": float(in_stock.quantize(Decimal("0.001"))),
                "to_order": float(to_order.quantize(Decimal("0.001")))
            })

    # Sort by name for readability
    parts_to_order.sort(key=lambda x: x["name"])

    log.info(f"Calculation complete. Parts to order: {len(parts_to_order)}")
    return parts_to_order
