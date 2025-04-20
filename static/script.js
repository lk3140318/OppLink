document.addEventListener('DOMContentLoaded', () => {
    const bypassForm = document.getElementById('bypassForm');
    const paheLinkInput = document.getElementById('paheLinkInput');
    const bypassButton = document.getElementById('bypassButton');
    const resultArea = document.getElementById('resultArea');
    const loadingIndicator = document.getElementById('loadingIndicator');

    bypassForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const paheUrl = paheLinkInput.value.trim();

        if (!paheUrl) {
            showResult('Please paste a Pahe.ink link first.', 'error');
            return;
        }

        // Basic client-side check (optional, backend does thorough check)
        if (!paheUrl.includes('pahe.ink') && !paheUrl.includes('pahe.li') && !paheUrl.includes('intercelestial.com')) {
             showResult('Invalid URL format. Please use a Pahe.ink or Pahe.li link.', 'error');
             return;
        }

        // Disable button and show loading indicator
        bypassButton.disabled = true;
        bypassButton.textContent = 'Bypassing...';
        loadingIndicator.style.display = 'block';
        resultArea.style.display = 'none'; // Hide previous results
        resultArea.className = ''; // Clear result area classes

        try {
            const response = await fetch('/bypass', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json' // Expect JSON response
                },
                body: JSON.stringify({ pahe_url: paheUrl })
            });

            const data = await response.json(); // Always try to parse JSON

            if (!response.ok) {
                // Handle HTTP errors (4xx, 5xx) - use error message from backend JSON
                 throw new Error(data.detail || `HTTP error! Status: ${response.status}`);
            }

            if (data.direct_link) {
                showResult(`<strong>Success!</strong> Direct Link:<br><a href="${data.direct_link}" target="_blank" rel="noopener noreferrer">${data.direct_link}</a>`, 'success');
            } else {
                // Should not happen if backend sends correct errors, but as fallback:
                throw new Error('Failed to extract the link. No link found in response.');
            }

        } catch (error) {
            console.error('Bypass Error:', error);
             // Display specific error message from backend or generic one
            showResult(`Error: ${error.message || 'Failed to process the link. Please check the link or try again later.'}`, 'error');
        } finally {
            // Re-enable button and hide loading indicator
            bypassButton.disabled = false;
            bypassButton.textContent = 'Bypass';
            loadingIndicator.style.display = 'none';
        }
    });

    function showResult(message, type = 'info') {
        resultArea.innerHTML = message;
        resultArea.className = type; // 'success' or 'error'
        resultArea.style.display = 'block';
    }
});
