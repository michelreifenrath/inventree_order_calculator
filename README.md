# InvenTree Order Calculator Plugin

An InvenTree plugin that provides a tool to calculate required components based on selected assemblies and desired quantities.

## Features

*   Provides a dedicated page within InvenTree.
*   Allows selection of multiple assembly parts.
*   Input desired quantity for each selected assembly.
*   Calculates the total required quantity for each base component by recursively exploding the Bill of Materials (BOM).
*   Checks current available stock levels.
*   Displays a list of components that need to be ordered (Required - In Stock > 0).

## Installation

1.  Install the plugin package (e.g., using `pip install .` from this directory within your InvenTree environment).
2.  Enable the "Order Calculator" plugin in the InvenTree admin interface (`Settings -> Plugins`).
3.  Ensure plugin background tasks are running (`invoke worker`).

## Usage

1.  Navigate to the "Calculate Orders" tab added to the main navigation sidebar.
2.  Use the search box to find and add assembly parts to the list.
3.  Enter the desired quantity to build for each assembly.
4.  Click the "Calculate Required Components" button.
5.  The results table will show the components that need to be ordered.
