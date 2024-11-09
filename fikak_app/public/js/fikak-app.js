// import { io } from "socket.io-client";

// const socket = io();

// console.log(socket)

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
 
    console.log("Frappe boot data is fully loaded.");
    // Your code here

    frappe.realtime.on('doc_bank_update', (data) => {
        debugger
        console.log(data)
    })
});

/*
socket = io('http://fikak.localhost:9000', {
    path: '/socket.io'
  })

socket.on('connect', () => {
console.log('Connected to Frappe WebSocket')
})

// Listen for events broadcast from Frappe
socket.on('doc_bank_update', data => {
debugger
const event = JSON.parse(data)
console.log('Document update received:', event)
})
*/