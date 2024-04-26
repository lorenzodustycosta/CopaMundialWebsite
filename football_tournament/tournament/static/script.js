function toggleAccordion(button) {
    var content = button.nextElementSibling;
    if (content.style.display === "block") {
        content.style.display = "none";
    } else {
        // Optionally close other open items
        var allContents = document.querySelectorAll('.accordion-content');
        allContents.forEach(function(otherContent) {
            if (otherContent !== content) {
                otherContent.style.display = 'none';
            }
        });
        content.style.display = "block";
    }
}
