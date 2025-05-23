/* eslint-env browser */
/* global django, getApiIcon, getApiUrl, inventreeGet, inventreePost, loadTableFilters, makeIconButton, renderDate, setupFilterList */
/* global showAlertOrCache, showApiError, showModalSpinner, hideModalSpinner */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Order Calculator JS loaded");

    const partSelect = document.getElementById('part-select');
    const addPartButton = document.getElementById('add-part-button');
    const targetTableBody = document.getElementById('target-assemblies-body');
    const targetPlaceholder = document.getElementById('target-assembly-placeholder');
    const calculateButton = document.getElementById('calculate-button');
    const calculationSpinner = document.getElementById('calculation-spinner');
    const resultsArea = document.getElementById('results-area');
    const resultsTableBody = document.getElementById('results-body');
    const resultsError = document.getElementById('results-error');
    const resultsSummary = document.getElementById('results-summary');

    let selectedTargets = {}; // Store selected part IDs and quantities: { partId: { name: "...", quantity: 1 } }

    // --- Initialize Part Selector ---
    console.log("Initializing select2 part selector...");
    $(partSelect).select2({
        ajax: {
            url: '/api/part/', // InvenTree API endpoint for parts
            dataType: 'json',
            delay: 250, // Wait 250ms after typing before querying
            data: function(params) {
                return {
                    search: params.term, // Search term
                    page: params.page || 1,
                    assembly: true, // Filter for assembly parts
                    active: true,   // Filter for active parts
                };
            },
            processResults: function(data, params) {
                params.page = params.page || 1;
                // Map API results to select2 format
                const results = data.results.map(part => ({
                    id: part.pk,
                    text: part.full_name || `${part.name} (ID: ${part.pk})`, // Use full_name if available
                    // Include other data if needed, accessible via select2('data')
                    name: part.name,
                    description: part.description,
                    ipn: part.IPN,
                }));

                return {
                    results: results,
                    pagination: {
                        more: data.next !== null // Check if there are more pages
                    }
                };
            },
            cache: true
        },
        placeholder: django.gettext('Search for an assembly part...'),
        minimumInputLength: 2, // Minimum characters to start searching
        allowClear: true,
        templateResult: function(data) {
            // Format how results look in the dropdown
            if (data.loading) {
                return data.text;
            }
            // Simple display: Name (IPN) - Description
            let text = data.text; // Already formatted as full_name or similar
            if (data.ipn) text += ` [${data.ipn}]`;
            if (data.description) text += ` - ${data.description}`;
            return text;
        },
        templateSelection: function(data) {
            // Format how the selected item looks
            return data.text || django.gettext('Select a part');
        }
    });


    // --- Event Listeners ---
    addPartButton.addEventListener('click', addSelectedPart);
    calculateButton.addEventListener('click', handleCalculation);
    targetTableBody.addEventListener('click', handleTableActions); // Delegate actions for remove buttons

    // --- Functions ---

    function addSelectedPart() {
        const selectedData = $(partSelect).select2('data');

        if (!selectedData || selectedData.length === 0 || !selectedData[0].id) {
            console.warn("No part selected in select2");
            showAlertOrCache({
                alert_id: 'order-calculator-no-part',
                title: django.gettext('No Part Selected'),
                message: django.gettext('Please select an assembly part from the dropdown.'),
                level: 'warning',
            });
            return;
        }

        const partData = selectedData[0];
        const partId = parseInt(partData.id, 10);
        // Use the text generated by select2, which should be the full name
        const partName = partData.text || `Part ${partId}`;

        if (selectedTargets[partId]) {
            console.warn(`Part ${partId} already added.`);
            showAlertOrCache({
                alert_id: `order-calculator-part-added-${partId}`,
                message: django.gettext(`Part ${partName} is already in the list.`),
                level: 'warning',
            });
            // Optionally highlight the existing row
            const existingRow = targetTableBody.querySelector(`tr[data-part-id="${partId}"]`);
            if (existingRow) {
                existingRow.classList.add('table-info');
                setTimeout(() => existingRow.classList.remove('table-info'), 1500);
            }
            return;
        }

        selectedTargets[partId] = { name: partName, quantity: 1 };
        renderTargetTable();
        // Reset the select2 selector
        $(partSelect).val(null).trigger('change');
    }

    function renderTargetTable() {
        targetTableBody.innerHTML = ''; // Clear existing rows
        let hasRows = false;

        for (const partId in selectedTargets) {
            hasRows = true;
            const target = selectedTargets[partId];
            const row = document.createElement('tr');
            row.setAttribute('data-part-id', partId);

            row.innerHTML = `
                <td>${target.name} (ID: ${partId})</td>
                <td>
                    <input type="number" class="form-control quantity-input" value="${target.quantity}" min="1" step="1" data-part-id="${partId}" style="width: 100px;">
                </td>
                <td>
                    <button class="btn btn-danger btn-sm remove-part-button" data-part-id="${partId}" title="${django.gettext('Remove Part')}">
                        <span class="fas fa-times"></span>
                    </button>
                </td>
            `;
            targetTableBody.appendChild(row);
        }

        if (!hasRows) {
            targetPlaceholder.style.display = ''; // Show placeholder
        } else {
            targetPlaceholder.style.display = 'none'; // Hide placeholder
        }
    }

    function handleTableActions(event) {
        const target = event.target;
        if (target.classList.contains('remove-part-button') || target.closest('.remove-part-button')) {
            const button = target.closest('.remove-part-button');
            const partId = button.getAttribute('data-part-id');
            if (partId) {
                delete selectedTargets[partId];
                renderTargetTable();
            }
        } else if (target.classList.contains('quantity-input')) {
            // Update quantity in selectedTargets when input changes
            const input = target;
            const partId = input.getAttribute('data-part-id');
            const newQuantity = parseInt(input.value, 10);
            if (partId && selectedTargets[partId] && !isNaN(newQuantity) && newQuantity >= 1) {
                selectedTargets[partId].quantity = newQuantity;
            } else {
                // Reset to previous value or 1 if invalid
                input.value = selectedTargets[partId] ? selectedTargets[partId].quantity : 1;
            }
        }
    }

    function handleCalculation() {
        console.log("Calculate button clicked");
        resultsArea.style.display = 'none';
        resultsError.style.display = 'none';
        resultsTableBody.innerHTML = '';
        resultsSummary.textContent = '';
        calculationSpinner.style.display = 'inline-block';
        calculateButton.disabled = true;

        const targetsPayload = Object.keys(selectedTargets).map(partId => ({
            part_id: parseInt(partId, 10),
            quantity: selectedTargets[partId].quantity
        }));

        if (targetsPayload.length === 0) {
            console.warn("No targets selected for calculation.");
            resultsError.textContent = django.gettext("Please add at least one assembly to calculate.");
            resultsError.style.display = 'block';
            resultsArea.style.display = 'block';
            calculationSpinner.style.display = 'none';
            calculateButton.disabled = false;
            return;
        }

        // Use inventreePost for API calls, handling CSRF automatically if configured
        inventreePost(
            '{% url "plugin:ordercalculator:calculate-api" %}', // Use Django URL reversing
            { targets: targetsPayload },
            {
                success: function(response) {
                    console.log("Calculation successful:", response);
                    if (response.success && response.results) {
                        displayResults(response.results);
                    } else {
                        // Handle case where success is true but no results (e.g., all in stock)
                         if (response.success && response.results.length === 0) {
                             resultsSummary.textContent = django.gettext("All required components are in stock. No orders needed.");
                             resultsArea.style.display = 'block';
                         } else {
                            throw new Error(response.error || django.gettext("Unknown error occurred during calculation."));
                         }
                    }
                },
                error: function(xhr, status, error) {
                    console.error("Calculation failed:", error);
                    let errorMsg = django.gettext("An error occurred during calculation.");
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMsg = xhr.responseJSON.error;
                    } else if (error) {
                        errorMsg += `: ${error}`;
                    }
                    resultsError.textContent = errorMsg;
                    resultsError.style.display = 'block';
                    resultsArea.style.display = 'block';
                },
                complete: function() {
                    calculationSpinner.style.display = 'none';
                    calculateButton.disabled = false;
                }
            }
        );
    }

    function displayResults(results) {
        resultsTableBody.innerHTML = ''; // Clear previous results

        if (results.length === 0) {
            resultsSummary.textContent = django.gettext("All required components are in stock. No orders needed.");
        } else {
            results.forEach(item => {
                const row = document.createElement('tr');
                // Add links to parts
                const partLink = `<a href="/part/${item.pk}/" target="_blank">${item.name}</a>`;
                row.innerHTML = `
                    <td>${item.pk}</td>
                    <td>${partLink}</td>
                    <td>${item.required}</td>
                    <td>${item.in_stock}</td>
                    <td class="text-danger fw-bold">${item.to_order}</td>
                `;
                resultsTableBody.appendChild(row);
            });
            resultsSummary.textContent = django.gettext(`Found ${results.length} components that need ordering.`);
        }
        resultsArea.style.display = 'block';
    }

    // Initial render in case there's state to restore (though unlikely here)
    renderTargetTable();
});
