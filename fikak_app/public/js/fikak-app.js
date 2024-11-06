function updateLogo() {
    debugger;
 
    // Change the logo by selecting the logo element
    const logo = document.querySelector("img.app-logo"); // Update selector if needed
    if (logo) {
        logo.src = "/assets/fikak_app/img/logo.png"; // Path to your custom logo
        logo.alt = "Waseera back-end"; // Optional: Set alt text for accessibility
    }

    $(".app-switcher-dropdown .sidebar-item-label").html("");

    $(".navbar-brand .app-logo").attr("src", "/assets/fikak_app/img/logo.png"); 

}
// Wait until the DOM is fully loaded
document.addEventListener("DOMContentLoaded", function() {
    frappe.ready(function() {
        console.log("All Frappe documents and the DOM are fully loaded.");
        // Your code to execute after everything is loaded
       
    });
    

});

// Wait until frappe.boot is available
function onFrappeLoad(callback) {
    if (typeof frappe.boot !== "undefined") {
        callback();
    } else {
        // Retry until frappe.boot is loaded
        setTimeout(() => onFrappeLoad(callback), 100);
    }
}

onFrappeLoad(function() {
    debugger;
    console.log("Frappe boot data is fully loaded.");
    // Your code here
});
$(document).on("page:load", function() {
    debugger;
    console.log("A new Frappe page has loaded.");
    // Your code for page load
});