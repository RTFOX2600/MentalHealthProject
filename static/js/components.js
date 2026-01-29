/**
 * Global UI Components Logic
 */

// 1. Numeric Stepper Logic
function adjustStepper(inputId, delta) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    let val = parseFloat(input.value) || 0;
    val += delta;
    
    const step = parseFloat(input.getAttribute('step')) || 1;
    const decimals = step.toString().split('.')[1]?.length || 0;
    input.value = val.toFixed(decimals);
    
    input.dispatchEvent(new Event('input', { bubbles: true }));
}

// 2. Custom Dropdown Logic
function initDropdowns() {
    document.querySelectorAll('.mh-custom-dropdown').forEach(dropdown => {
        const trigger = dropdown.querySelector('.mh-dropdown-trigger');
        const items = dropdown.querySelectorAll('.mh-dropdown-item');
        const hiddenInput = dropdown.querySelector('input[type="hidden"]');
        const selectedText = dropdown.querySelector('.selected-text');

        if (!trigger || dropdown.dataset.initialized) return;

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.mh-custom-dropdown.active').forEach(active => {
                if (active !== dropdown) active.classList.remove('active');
            });
            dropdown.classList.toggle('active');
        });

        items.forEach(item => {
            item.addEventListener('click', () => {
                const value = item.getAttribute('data-value');
                const text = item.innerText;
                if (selectedText) selectedText.innerText = text;
                if (hiddenInput) hiddenInput.value = value;
                items.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                dropdown.classList.remove('active');
                
                // Trigger change event on hidden input
                if (hiddenInput) hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });
        
        dropdown.dataset.initialized = "true";
    });
}

// Global click handler to close dropdowns
document.addEventListener('click', () => {
    document.querySelectorAll('.mh-custom-dropdown.active').forEach(dropdown => {
        dropdown.classList.remove('active');
    });
});

// Initialize on load
window.addEventListener('DOMContentLoaded', initDropdowns);
