/* RailYatra — Main JavaScript */

// ── Auto-dismiss flash messages ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(f => {
    setTimeout(() => f.style.display='none', 4000);
  });

  // Set today's date as min for date inputs
  const today = new Date().toISOString().split('T')[0];
  document.querySelectorAll('input[type="date"]').forEach(d => {
    d.min = today;
    if (!d.value) d.value = today;
  });

  // Admin date
  const ad = document.getElementById('adminDate');
  if (ad) {
    ad.textContent = new Date().toLocaleDateString('en-IN',
      {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  }

  // Seat map builder
  if (document.getElementById('seatMap')) buildSeatMap();

  // Booking step on load
  if (document.querySelector('.p-step')) showStep(1);
});

// ── Seat Map ──
let selectedSeat = null;
const BOOKED = [3,7,11,15,19,24,28,32,36,40,44,48];

function buildSeatMap() {
  const map = document.getElementById('seatMap');
  if (!map) return;
  let html = '';
  for (let i = 1; i <= 72; i++) {
    const b = BOOKED.includes(i);
    html += `<div class="seat ${b?'booked':'avail'}" onclick="pickSeat(this,${i})">${b?'':i}</div>`;
  }
  map.innerHTML = html;
}

function pickSeat(el, num) {
  if (el.classList.contains('booked')) return;
  document.querySelectorAll('.seat.picked').forEach(s => {
    s.classList.replace('picked','avail');
  });
  el.classList.replace('avail','picked');
  selectedSeat = num;
  const inp = document.getElementById('seatInput');
  if (inp) inp.value = 'S1-' + num;
}

// ── Booking Steps ──
let currentStep = 1;

function showStep(n) {
  for (let i = 1; i <= 4; i++) {
    const section = document.getElementById('bStep' + i);
    const circle  = document.getElementById('pStep' + i);
    if (section) section.style.display = (i === n) ? 'block' : 'none';
    if (circle) {
      circle.classList.remove('active','done');
      if (i === n) circle.classList.add('active');
      if (i < n)  circle.classList.add('done');
    }
  }
  currentStep = n;
  window.scrollTo({top:0, behavior:'smooth'});
  if (n === 2) buildSeatMap();
}

function nextStep() { showStep(currentStep + 1); }
function prevStep() { showStep(currentStep - 1); }

// ── Coach Selection ──
function pickCoach(el) {
  document.querySelectorAll('.coach-opt').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  const coachId = el.dataset.coachId;
  const fare    = el.dataset.fare;
  const inp = document.getElementById('coachInput');
  if (inp) inp.value = coachId;
  const fareInp = document.getElementById('fareInput');
  if (fareInp) fareInp.value = fare;
  updateSummaryFare(fare, el.querySelector('.co-type').textContent, el.querySelector('.co-price').textContent);
}

function updateSummaryFare(fare, cls, price) {
  const el = document.getElementById('summaryFare');
  if (el) el.textContent = price;
  const clsEl = document.getElementById('summaryClass');
  if (clsEl) clsEl.textContent = cls;
  const totalEl = document.getElementById('summaryTotal');
  if (totalEl) {
    const base = parseFloat(fare) || 0;
    const rsv  = 40;
    const gst  = Math.round((base + rsv) * 0.05);
    const total = base + rsv + gst;
    totalEl.textContent = '₹' + total.toLocaleString('en-IN');
    const totalInp = document.getElementById('totalInput');
    if (totalInp) totalInp.value = total;
  }
}

// ── Payment Method ──
function pickPayment(el) {
  document.querySelectorAll('.pay-opt').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
  const mInp = document.getElementById('payMethodInput');
  if (mInp) mInp.value = el.dataset.method;
}

// ── PNR Search (also handled server-side) ──
function searchPNR() {
  const val = document.getElementById('pnrField').value.trim();
  if (!val) { alert('Please enter a PNR number.'); return; }
  window.location.href = '/pnr/' + val;
}

// ── Admin sidebar active ──
function setActive(el) {
  document.querySelectorAll('.sb-item').forEach(s => s.classList.remove('active'));
  el.classList.add('active');
}

// ── Confirm cancel ──
function confirmCancel(pnr) {
  if (confirm('Are you sure you want to cancel booking ' + pnr + '? This cannot be undone.')) {
    window.location.href = '/cancel/' + pnr;
  }
}