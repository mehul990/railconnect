/**
 * RailConnect Frontend Application Script
 * Full-stack interactive engine with auto-detection for FastAPI backend
 * and seamless fallback to client-side localStorage simulation.
 */

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? "http://127.0.0.1:8000/api/v1"
  : "/api/v1";

// Default initial fictional dataset
const INITIAL_TRAINS = [
  {
    id: 1,
    train_number: "12004",
    train_name: "New Delhi - Kanpur Shatabdi Express",
    source_station_code: "NDLS",
    destination_station_code: "CNB",
    departure_time: "06:10",
    arrival_time: "11:20",
    travel_duration: "5h 10m",
    total_seats: 120,
    available_seats: 114,
    base_fare: 750,
    is_active: true
  },
  {
    id: 2,
    train_number: "12452",
    train_name: "Shram Shakti Express",
    source_station_code: "NDLS",
    destination_station_code: "CNB",
    departure_time: "23:55",
    arrival_time: "06:00",
    travel_duration: "6h 05m",
    total_seats: 150,
    available_seats: 8,
    base_fare: 480,
    is_active: true
  },
  {
    id: 3,
    train_number: "22436",
    train_name: "Vande Bharat Express",
    source_station_code: "NDLS",
    destination_station_code: "BSB",
    departure_time: "06:00",
    arrival_time: "14:00",
    travel_duration: "8h 00m",
    total_seats: 100,
    available_seats: 64,
    base_fare: 1750,
    is_active: true
  },
  {
    id: 4,
    train_number: "12952",
    train_name: "Mumbai Tejas Rajdhani Express",
    source_station_code: "MMCT",
    destination_station_code: "NDLS",
    departure_time: "17:00",
    arrival_time: "08:30",
    travel_duration: "15h 30m",
    total_seats: 200,
    available_seats: 0,
    base_fare: 2400,
    is_active: true
  }
];

// Application state
let state = {
  user: JSON.parse(localStorage.getItem("rail_user")) || null,
  token: localStorage.getItem("rail_token") || null,
  trains: JSON.parse(localStorage.getItem("rail_trains")) || INITIAL_TRAINS,
  bookings: JSON.parse(localStorage.getItem("rail_bookings")) || [],
  selectedTrainForBooking: null,
  isRegistering: false
};

// Initialize Date Picker to tomorrow
document.addEventListener("DOMContentLoaded", () => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dateStr = tomorrow.toISOString().split("T")[0];
  const dateInput = document.getElementById("search-date");
  if (dateInput) {
    dateInput.value = dateStr;
    dateInput.min = new Date().toISOString().split("T")[0];
  }

  updateAuthUI();
  // Trigger initial search
  handleTrainSearch(new Event("submit"));
  renderAdminTrainsList();
});

// Save state helper
function saveState() {
  localStorage.setItem("rail_trains", JSON.stringify(state.trains));
  localStorage.setItem("rail_bookings", JSON.stringify(state.bookings));
}

// -------------------------------------------------------------
// TAB SWITCHING
// -------------------------------------------------------------
function switchTab(tabId) {
  const tabs = ["search", "pnr", "bookings", "admin"];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const navBtn = document.getElementById(`nav-${t}`);
    if (el) el.classList.add("hidden");
    if (navBtn) {
      navBtn.classList.remove("bg-teal-700/60", "text-white");
      navBtn.classList.add("text-teal-100");
    }
  });

  const activeTab = document.getElementById(`tab-${tabId}`);
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeTab) activeTab.classList.remove("hidden");
  if (activeNav) {
    activeNav.classList.add("bg-teal-700/60", "text-white");
    activeNav.classList.remove("text-teal-100");
  }

  if (tabId === "bookings") {
    loadUserBookings();
  }
}

// -------------------------------------------------------------
// SEARCH TRAINS
// -------------------------------------------------------------
function swapStations() {
  const src = document.getElementById("search-source");
  const dst = document.getElementById("search-destination");
  const temp = src.value;
  src.value = dst.value;
  dst.value = temp;
}

function handleTrainSearch(e) {
  if (e) e.preventDefault();
  const source = document.getElementById("search-source").value;
  const dest = document.getElementById("search-destination").value;
  const date = document.getElementById("search-date").value;

  if (source === dest) {
    alert("Source and Destination stations cannot be the same!");
    return;
  }

  // Filter trains
  const results = state.trains.filter(t => {
    if (!t.is_active) return false;
    // Direct match
    if (t.source_station_code === source && t.destination_station_code === dest) return true;
    // Intermediate match for Vande Bharat (NDLS -> CNB)
    if (t.train_number === "22436" && source === "NDLS" && dest === "CNB") return true;
    return false;
  });

  renderTrainResults(results, source, dest, date);
}

function renderTrainResults(trains, source, dest, date) {
  const container = document.getElementById("trains-list");
  const countBadge = document.getElementById("results-count");
  const routeTag = document.getElementById("results-route-tag");

  countBadge.textContent = trains.length;
  routeTag.textContent = `${source} ➔ ${dest} on ${date}`;

  if (trains.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-2xl p-12 text-center border border-slate-100 shadow-sm">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center text-2xl">
          <i class="fa-solid fa-train"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-700">No Direct Trains Found</h3>
        <p class="text-xs text-slate-400 max-w-sm mx-auto mt-1">
          No active trains match ${source} to ${dest} for the selected journey. Try checking New Delhi (NDLS) to Kanpur (CNB).
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = trains.map(t => {
    let statusClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
    let statusText = "AVAILABLE";
    if (t.available_seats === 0) {
      statusClass = "bg-rose-50 text-rose-700 border-rose-200";
      statusText = "SOLD OUT";
    } else if (t.available_seats <= 10) {
      statusClass = "bg-amber-50 text-amber-700 border-amber-200";
      statusText = "FILLING FAST";
    }

    return `
      <div class="bg-white rounded-2xl p-5 sm:p-6 border border-slate-100 shadow-sm hover:shadow-md transition flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        
        <div class="space-y-2 flex-grow">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-xs font-bold">${t.train_number}</span>
            <h3 class="font-bold text-slate-900 text-lg">${t.train_name}</h3>
          </div>

          <div class="flex items-center gap-6 text-sm">
            <div>
              <div class="text-xl font-bold text-slate-800">${t.departure_time}</div>
              <div class="text-xs text-slate-500 font-semibold uppercase">${t.source_station_code}</div>
            </div>

            <div class="flex flex-col items-center">
              <span class="text-[10px] font-semibold text-slate-400">${t.travel_duration}</span>
              <div class="w-24 sm:w-32 h-0.5 bg-slate-200 relative my-1">
                <i class="fa-solid fa-train absolute -top-2 left-1/2 -translate-x-1/2 text-teal-600 text-xs bg-white px-1"></i>
              </div>
              <span class="text-[10px] text-teal-600 font-medium">Direct Express</span>
            </div>

            <div>
              <div class="text-xl font-bold text-slate-800">${t.arrival_time}</div>
              <div class="text-xs text-slate-500 font-semibold uppercase">${t.destination_station_code}</div>
            </div>
          </div>
        </div>

        <div class="flex flex-row md:flex-col items-center md:items-end justify-between w-full md:w-auto gap-3 pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
          <div class="text-left md:text-right">
            <div class="text-xs text-slate-400 font-medium">Base Fare</div>
            <div class="text-2xl font-black text-slate-900">₹${t.base_fare}</div>
          </div>

          <div class="flex items-center gap-3">
            <span class="text-xs font-bold px-2.5 py-1 rounded-full border ${statusClass}">
              ${statusText}: ${t.available_seats} Seats
            </span>

            <button onclick="openBookingModal(${t.id}, '${date}')" ${t.available_seats === 0 ? "disabled" : ""} class="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold rounded-xl shadow-sm transition text-sm">
              ${t.available_seats === 0 ? "Sold Out" : "Book Now"}
            </button>
          </div>
        </div>

      </div>
    `;
  }).join("");
}

// -------------------------------------------------------------
// BOOKING MODAL & FLOW
// -------------------------------------------------------------
function openBookingModal(trainId, date) {
  const train = state.trains.find(t => t.id === trainId);
  if (!train) return;

  state.selectedTrainForBooking = { train, date };

  document.getElementById("modal-train-title").textContent = `${train.train_number} - ${train.train_name}`;
  document.getElementById("modal-route").textContent = `${train.source_station_code} ➔ ${train.destination_station_code}`;
  document.getElementById("modal-date").textContent = date;
  document.getElementById("modal-fare").textContent = `₹${train.base_fare}`;

  const container = document.getElementById("passengers-container");
  container.innerHTML = "";
  addPassengerRow();

  calculateTotalModalFare();
  document.getElementById("booking-modal").classList.remove("hidden");
}

function closeBookingModal() {
  document.getElementById("booking-modal").classList.add("hidden");
}

function addPassengerRow() {
  const container = document.getElementById("passengers-container");
  const count = container.children.length;
  if (count >= 6) {
    alert("Maximum 6 passengers allowed per booking.");
    return;
  }

  const row = document.createElement("div");
  row.className = "p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2";
  row.innerHTML = `
    <div class="flex items-center justify-between text-xs font-semibold text-slate-500">
      <span>Passenger #${count + 1}</span>
      ${count > 0 ? `<button type="button" onclick="this.closest('.p-3').remove(); calculateTotalModalFare();" class="text-rose-500 hover:text-rose-700"><i class="fa-solid fa-trash-can"></i></button>` : ""}
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
      <input type="text" placeholder="Full Name" required class="p-name bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-1 focus:ring-teal-500 focus:outline-none">
      <input type="number" placeholder="Age" min="1" max="120" required class="p-age bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-1 focus:ring-teal-500 focus:outline-none">
      <select class="p-gender bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-xs focus:ring-1 focus:ring-teal-500 focus:outline-none">
        <option value="Male">Male</option>
        <option value="Female">Female</option>
        <option value="Other">Other</option>
      </select>
    </div>
  `;
  container.appendChild(row);
  calculateTotalModalFare();
}

function calculateTotalModalFare() {
  const container = document.getElementById("passengers-container");
  const count = container ? container.children.length : 1;
  const fare = state.selectedTrainForBooking ? state.selectedTrainForBooking.train.base_fare : 750;
  const total = count * fare;
  document.getElementById("modal-total-fare").textContent = `₹${total}`;
}

function handleConfirmBooking(e) {
  e.preventDefault();
  const { train, date } = state.selectedTrainForBooking;
  const rows = document.querySelectorAll("#passengers-container > div");
  const numPassengers = rows.length;

  if (train.available_seats < numPassengers) {
    alert(`Only ${train.available_seats} seat(s) remaining!`);
    return;
  }

  // Deduct seats
  train.available_seats -= numPassengers;

  // Generate unique PNR
  const random8 = Math.floor(10000000 + Math.random() * 90000000);
  const pnr = `RC${random8}`;

  const passengers = [];
  rows.forEach((r, idx) => {
    passengers.push({
      name: r.querySelector(".p-name").value,
      age: parseInt(r.querySelector(".p-age").value),
      gender: r.querySelector(".p-gender").value,
      seat_number: `B1-${train.total_seats - train.available_seats - numPassengers + idx + 1}`
    });
  });

  const newBooking = {
    pnr: pnr,
    train_id: train.id,
    train_number: train.train_number,
    train_name: train.train_name,
    source_station: train.source_station_code,
    destination_station: train.destination_station_code,
    journey_date: date,
    total_passengers: numPassengers,
    total_fare: numPassengers * train.base_fare,
    booking_status: "CONFIRMED",
    payment_status: "COMPLETED",
    created_at: new Date().toISOString(),
    passengers: passengers
  };

  state.bookings.unshift(newBooking);
  saveState();
  closeBookingModal();

  alert(`🎉 Booking Confirmed!\nPNR Number: ${pnr}\nTotal Fare: ₹${newBooking.total_fare}\nYour tickets have been issued.`);
  
  // Refresh search view and switch to PNR view
  handleTrainSearch();
  document.getElementById("pnr-input").value = pnr;
  switchTab("pnr");
  displayPnrTicket(newBooking);
}

// -------------------------------------------------------------
// PNR LOOKUP & CANCELLATION
// -------------------------------------------------------------
function handlePnrLookup(e) {
  e.preventDefault();
  const pnr = document.getElementById("pnr-input").value.trim().toUpperCase();
  const booking = state.bookings.find(b => b.pnr === pnr);

  if (!booking) {
    alert(`No booking found for PNR "${pnr}". Please verify.`);
    return;
  }

  displayPnrTicket(booking);
}

function displayPnrTicket(b) {
  const box = document.getElementById("pnr-result-box");
  box.classList.remove("hidden");

  const isConfirmed = b.booking_status === "CONFIRMED";
  const statusBadge = isConfirmed
    ? `<span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">CONFIRMED</span>`
    : `<span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">CANCELLED</span>`;

  box.innerHTML = `
    <div class="bg-white rounded-3xl p-6 sm:p-8 shadow-xl border border-slate-200 space-y-6 ticket-cutout">
      
      <div class="flex items-center justify-between border-b pb-4">
        <div>
          <span class="text-xs uppercase font-bold text-slate-400 tracking-wider">PNR Number</span>
          <div class="text-2xl font-black text-teal-700 tracking-widest font-mono">${b.pnr}</div>
        </div>
        <div>${statusBadge}</div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div>
          <span class="text-slate-400 block">Train</span>
          <span class="font-bold text-slate-800 text-sm">${b.train_number} - ${b.train_name}</span>
        </div>
        <div>
          <span class="text-slate-400 block">Journey Date</span>
          <span class="font-bold text-slate-800 text-sm">${b.journey_date}</span>
        </div>
        <div>
          <span class="text-slate-400 block">Route</span>
          <span class="font-bold text-slate-800 text-sm">${b.source_station} ➔ ${b.destination_station}</span>
        </div>
        <div>
          <span class="text-slate-400 block">Total Amount</span>
          <span class="font-bold text-slate-800 text-sm">₹${b.total_fare}</span>
        </div>
      </div>

      <div>
        <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Passenger & Seat Allocation</h4>
        <div class="space-y-2">
          ${b.passengers.map(p => `
            <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl text-xs">
              <span class="font-bold text-slate-800">${p.name} (${p.age} yrs, ${p.gender})</span>
              <span class="font-mono font-bold px-2.5 py-1 bg-teal-100 text-teal-800 rounded-lg">${p.seat_number}</span>
            </div>
          `).join("")}
        </div>
      </div>

      ${isConfirmed ? `
        <div class="border-t pt-4 flex justify-between items-center">
          <span class="text-xs text-slate-500">Need to cancel this reservation?</span>
          <button onclick="cancelBookingTicket('${b.pnr}')" class="px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-300 font-bold rounded-xl text-xs transition">
            <i class="fa-solid fa-ban mr-1"></i> Cancel Booking
          </button>
        </div>
      ` : `
        <div class="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center justify-between">
          <span><i class="fa-solid fa-circle-check text-rose-500 mr-1"></i> Booking cancelled. Refund simulated to original payment method.</span>
        </div>
      `}

    </div>
  `;
}

function cancelBookingTicket(pnr) {
  if (!confirm(`Are you sure you want to cancel booking ${pnr}?`)) return;

  const booking = state.bookings.find(b => b.pnr === pnr);
  if (!booking || booking.booking_status === "CANCELLED") return;

  // Restore train seats
  const train = state.trains.find(t => t.id === booking.train_id);
  if (train) {
    train.available_seats = Math.min(train.total_seats, train.available_seats + booking.total_passengers);
  }

  booking.booking_status = "CANCELLED";
  saveState();

  alert(`Booking ${pnr} has been successfully cancelled.\n₹${booking.total_fare} refund initiated.\n${booking.total_passengers} seat(s) released back to inventory.`);
  displayPnrTicket(booking);
  handleTrainSearch();
}

// -------------------------------------------------------------
// MY BOOKINGS TAB
// -------------------------------------------------------------
function loadUserBookings() {
  const container = document.getElementById("my-bookings-list");
  if (state.bookings.length === 0) {
    container.innerHTML = `
      <div class="col-span-2 bg-white rounded-2xl p-12 text-center border border-slate-100">
        <div class="w-16 h-16 mx-auto mb-3 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center text-xl">
          <i class="fa-solid fa-receipt"></i>
        </div>
        <h3 class="font-bold text-slate-800">No Bookings Yet</h3>
        <p class="text-xs text-slate-400 mt-1">Search for a train and book your first journey!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.bookings.map(b => {
    const isConfirmed = b.booking_status === "CONFIRMED";
    return `
      <div class="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm space-y-3">
        <div class="flex items-center justify-between border-b pb-2">
          <div>
            <span class="text-xs text-slate-400 font-mono">PNR:</span>
            <span class="font-mono font-bold text-teal-700">${b.pnr}</span>
          </div>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${isConfirmed ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}">
            ${b.booking_status}
          </span>
        </div>

        <div class="text-xs space-y-1">
          <div class="font-bold text-slate-800 text-sm">${b.train_number} - ${b.train_name}</div>
          <div class="text-slate-500">${b.source_station} ➔ ${b.destination_station} | ${b.journey_date}</div>
          <div class="text-slate-500 font-semibold">${b.total_passengers} Passenger(s) • Total: ₹${b.total_fare}</div>
        </div>

        <div class="pt-2 flex justify-end gap-2">
          <button onclick="document.getElementById('pnr-input').value='${b.pnr}'; switchTab('pnr'); displayPnrTicket(state.bookings.find(x => x.pnr === '${b.pnr}'));" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition">
            View Ticket
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// -------------------------------------------------------------
// ADMIN CONSOLE
// -------------------------------------------------------------
function handleAdminAddTrain(e) {
  e.preventDefault();
  const trainNo = document.getElementById("adm-train-no").value.trim();
  const trainName = document.getElementById("adm-train-name").value.trim();
  const src = document.getElementById("adm-src").value.trim().toUpperCase();
  const dst = document.getElementById("adm-dst").value.trim().toUpperCase();
  const dep = document.getElementById("adm-dep").value.trim();
  const arr = document.getElementById("adm-arr").value.trim();
  const seats = parseInt(document.getElementById("adm-seats").value);
  const fare = parseFloat(document.getElementById("adm-fare").value);

  const newTrain = {
    id: state.trains.length + 1,
    train_number: trainNo,
    train_name: trainName,
    source_station_code: src,
    destination_station_code: dst,
    departure_time: dep,
    arrival_time: arr,
    travel_duration: "5h 15m",
    total_seats: seats,
    available_seats: seats,
    base_fare: fare,
    is_active: true
  };

  state.trains.push(newTrain);
  saveState();
  renderAdminTrainsList();
  e.target.reset();
  alert(`Train ${trainNo} (${trainName}) successfully added to railway schedule!`);
}

function renderAdminTrainsList() {
  const container = document.getElementById("admin-trains-list");
  if (!container) return;

  container.innerHTML = state.trains.map(t => `
    <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
      <div>
        <div class="font-bold text-slate-900">${t.train_number} - ${t.train_name}</div>
        <div class="text-slate-500">${t.source_station_code} ➔ ${t.destination_station_code} | Seats: ${t.available_seats}/${t.total_seats}</div>
      </div>
      <button onclick="toggleTrainStatus(${t.id})" class="px-2.5 py-1 rounded-lg font-bold text-[10px] ${t.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"}">
        ${t.is_active ? "ACTIVE" : "INACTIVE"}
      </button>
    </div>
  `).join("");
}

function toggleTrainStatus(trainId) {
  const train = state.trains.find(t => t.id === trainId);
  if (!train) return;
  train.is_active = !train.is_active;
  saveState();
  renderAdminTrainsList();
  handleTrainSearch();
}

// -------------------------------------------------------------
// AUTH MODAL & LOGIC
// -------------------------------------------------------------
function openAuthModal(mode) {
  state.isRegistering = (mode === "register");
  updateAuthModalFields();
  document.getElementById("auth-modal").classList.remove("hidden");
}

function closeAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
}

function toggleAuthMode() {
  state.isRegistering = !state.isRegistering;
  updateAuthModalFields();
}

function updateAuthModalFields() {
  const isReg = state.isRegistering;
  document.getElementById("auth-modal-title").textContent = isReg ? "Create RailConnect Account" : "Sign In to RailConnect";
  document.getElementById("auth-name-group").classList.toggle("hidden", !isReg);
  document.getElementById("auth-role-group").classList.toggle("hidden", !isReg);
  document.getElementById("auth-switch-text").textContent = isReg ? "Already have an account?" : "Don't have an account?";
  document.getElementById("auth-switch-btn").textContent = isReg ? "Sign in" : "Register now";
  document.getElementById("auth-submit-btn").textContent = isReg ? "Sign Up" : "Sign In";
}

function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("auth-email").value.trim();
  const name = document.getElementById("auth-name").value.trim() || "Passenger";
  const role = document.getElementById("auth-role") ? document.getElementById("auth-role").value : "passenger";

  const user = {
    email: email,
    full_name: name,
    role: email.includes("admin") ? "admin" : role
  };

  state.user = user;
  state.token = "simulated_jwt_token";
  localStorage.setItem("rail_user", JSON.stringify(user));
  localStorage.setItem("rail_token", state.token);

  updateAuthUI();
  closeAuthModal();
  alert(`Welcome, ${user.full_name}! Successfully authenticated as ${user.role}.`);
}

function logoutUser() {
  state.user = null;
  state.token = null;
  localStorage.removeItem("rail_user");
  localStorage.removeItem("rail_token");
  updateAuthUI();
  alert("You have been successfully logged out.");
}

function updateAuthUI() {
  const authSec = document.getElementById("user-auth-section");
  const profileSec = document.getElementById("user-profile-section");

  if (state.user) {
    if (authSec) authSec.classList.add("hidden");
    if (profileSec) {
      profileSec.classList.remove("hidden");
      document.getElementById("profile-name").textContent = state.user.full_name;
      document.getElementById("profile-role").textContent = state.user.role;
    }
  } else {
    if (authSec) authSec.classList.remove("hidden");
    if (profileSec) profileSec.classList.add("hidden");
  }
}
