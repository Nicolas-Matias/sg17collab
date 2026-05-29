/**
 * ITU-T Report Generator - Frontend Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const form = document.getElementById('reportForm');
    const reportTypeInputs = document.querySelectorAll('input[name="reportType"]');
    const wpField = document.getElementById('wpField');
    const questionField = document.getElementById('questionField');
    const questionWpField = document.getElementById('questionWpField');
    const generateBtn = document.getElementById('generateBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const progressMsg = document.getElementById('progressMsg');
    const successMsg = document.getElementById('successMsg');
    const errorMsg = document.getElementById('errorMsg');
    const downloadLink = document.getElementById('downloadLink');
    const errorText = document.getElementById('errorText');
    const jsonPreview = document.getElementById('jsonPreview');

    // ============================================
    // Toggle WP/Question Fields
    // ============================================
    reportTypeInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Hide download link and messages when switching report type
            successMsg.classList.add('d-none');
            errorMsg.classList.add('d-none');

            if (this.value === 'wp') {
                // Show WP fields, hide Question fields
                wpField.classList.remove('d-none');
                questionField.classList.add('d-none');
                questionWpField.classList.add('d-none');

                // Set required attributes
                document.getElementById('workingParty').required = true;
                document.getElementById('question').required = false;
            } else {
                // Show Question fields, hide WP fields
                wpField.classList.add('d-none');
                questionField.classList.remove('d-none');
                questionWpField.classList.remove('d-none');

                // Set required attributes
                document.getElementById('workingParty').required = false;
                document.getElementById('question').required = true;
            }
            updateJsonPreview();
        });
    });

    // ============================================
    // Build Config Object
    // ============================================
    function buildConfig() {
        const formData = new FormData(form);
        const reportType = formData.get('reportType');

        const config = {
            group: parseInt(formData.get('group')) || 17,
            start: convertDateToITUFormat(formData.get('start'))
            // end date and place are auto-detected from ITU website
        };

        // Add next_meeting if provided
        const nextMeeting = formData.get('next_meeting');
        if (nextMeeting) {
            config.next_meeting = convertDateToITUFormat(nextMeeting);
        }

        // Add type-specific fields
        if (reportType === 'wp') {
            config.workingParty = parseInt(formData.get('workingParty')) || 1;
        } else {
            config.question = parseInt(formData.get('question')) || 10;
        }

        return { config, reportType };
    }

    // ============================================
    // JSON Preview Update
    // ============================================
    function updateJsonPreview() {
        const { config } = buildConfig();
        jsonPreview.textContent = JSON.stringify(config, null, 2);
    }

    // Update preview when any input changes
    form.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', updateJsonPreview);
        input.addEventListener('change', updateJsonPreview);
    });

    // Initial preview
    updateJsonPreview();

    // ============================================
    // Form Submission
    // ============================================
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Hide previous messages
        hideAllMessages();

        // Show progress
        showProgress();

        // Disable submit button
        generateBtn.disabled = true;

        // Get config
        const { config, reportType } = buildConfig();

        // Determine API endpoint
        const endpoint = reportType === 'wp'
            ? '/api/generate-wp-report'
            : '/api/generate-question-report';

        try {
            // Call API
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                // Success!
                showSuccess(result.download_id, result.filename);
            } else {
                // Error from backend
                showError(result.error || 'Unknown error occurred');
            }
        } catch (error) {
            // Network or parsing error
            showError(`Network error: ${error.message}`);
        } finally {
            // Re-enable submit button
            generateBtn.disabled = false;
        }
    });

    // ============================================
    // Helper Functions
    // ============================================

    /**
     * Convert HTML date input (YYYY-MM-DD) to ITU format (YYYY/MM/DD)
     */
    function convertDateToITUFormat(dateStr) {
        if (!dateStr) return '';
        return dateStr.replace(/-/g, '/');
    }

    /**
     * Hide all message boxes
     */
    function hideAllMessages() {
        progressMsg.classList.add('d-none');
        successMsg.classList.add('d-none');
        errorMsg.classList.add('d-none');
    }

    /**
     * Show progress message
     */
    function showProgress() {
        btnText.classList.add('d-none');
        btnSpinner.classList.remove('d-none');
        progressMsg.classList.remove('d-none');
    }

    /**
     * Show success message with download link
     */
    function showSuccess(downloadId, filename) {
        btnText.classList.remove('d-none');
        btnSpinner.classList.add('d-none');
        progressMsg.classList.add('d-none');

        // Set download link
        downloadLink.href = `/api/download/${downloadId}`;
        downloadLink.download = filename;

        successMsg.classList.remove('d-none');

        // Scroll to success message
        successMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    /**
     * Show error message
     */
    function showError(message) {
        btnText.classList.remove('d-none');
        btnSpinner.classList.add('d-none');
        progressMsg.classList.add('d-none');

        errorText.textContent = message;
        errorMsg.classList.remove('d-none');

        // Scroll to error message
        errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // End date is now auto-detected from ITU website - no client-side validation needed
});
