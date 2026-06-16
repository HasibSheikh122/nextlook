// Add this to your admin JS file or in the template
document.addEventListener('DOMContentLoaded', function() {
    // Fix for AdminLTE dropdowns
    if (typeof $.fn.dropdown !== 'undefined') {
        $('.dropdown-toggle').dropdown();
    }
    
    // Fix for select2 dropdowns
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            dropdownAutoWidth: true,
            width: '100%'
        });
    }
    
    // Ensure all dropdowns have proper z-index
    $('.dropdown-menu').each(function() {
        $(this).css('z-index', '9999');
    });
});