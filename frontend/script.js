/* ═══════════════════════════════════════════════════════════════════
   Brickfolio — Shared JavaScript
   ═══════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000';

// ─── User ID ──────────────────────────────────────────────────────────────
function getUserId() {
  let uid = localStorage.getItem('bf_uid');
  if (!uid) {
    uid = 'u_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    localStorage.setItem('bf_uid', uid);
  }
  return uid;
}
const USER_ID = getUserId();

// ─── State ────────────────────────────────────────────────────────────────
let userLat = null;
let userLng = null;
let likedProps = JSON.parse(localStorage.getItem('bf_liked') || '[]');

// ─── Location Detection ───────────────────────────────────────────────────
function requestLocation(onSuccess) {
  if (!navigator.geolocation) { detectByIP(onSuccess); return; }
  navigator.geolocation.getCurrentPosition(
    pos => {
      userLat = pos.coords.latitude;
      userLng = pos.coords.longitude;
      setLocationDisplay('Pune Area', true);
      pushLocation(userLat, userLng);
      if (onSuccess) onSuccess(userLat, userLng);
    },
    () => detectByIP(onSuccess)
  );
}

async function detectByIP(onSuccess) {
  try {
    const r = await fetch(`${API}/api/detect-location`);
    const d = await r.json();
    userLat = d.latitude; userLng = d.longitude;
    setLocationDisplay(d.city || 'Pune', false);
  } catch {
    userLat = 18.5204; userLng = 73.8567;
    setLocationDisplay('Pune', false);
  }
  pushLocation(userLat, userLng);
  if (onSuccess) onSuccess(userLat, userLng);
}

function setLocationDisplay(city, isGPS) {
  const label = document.getElementById('locationLabel');
  const dot   = document.getElementById('locDot');
  if (label) label.textContent = city;
  if (dot) {
    dot.style.background  = isGPS ? 'var(--ok)' : 'var(--warn)';
    dot.style.boxShadow   = isGPS ? '0 0 8px var(--ok)' : '0 0 8px var(--warn)';
  }
}

async function pushLocation(lat, lng) {
  try {
    await fetch(`${API}/api/update-location`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, latitude: lat, longitude: lng }),
    });
  } catch {}
}

// ─── Track Events ─────────────────────────────────────────────────────────
async function trackView(propId, type = 'view') {
  try {
    await fetch(`${API}/api/track-view`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, property_id: propId, action_type: type }),
    });
  } catch {}
}

async function trackSearch(query, location = '') {
  try {
    await fetch(`${API}/api/search`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, query, location: location || query }),
    });
  } catch {}
}

// ─── Property Card HTML ───────────────────────────────────────────────────
function propertyCard(p, idx = 0, showScore = false) {
  const badge  = getBadgeClass(p.badge);
  const liked  = likedProps.includes(p.property_id);
  const score  = p._ai_score || Math.floor(70 + Math.random() * 28);
  const dataP  = JSON.stringify(p).replace(/"/g, '&quot;');
  return `
  <div class="property-card" style="animation-delay:${idx * .06}s"
       onclick="openModalData(${dataP})">
    <div class="card-image">
      <img src="${p.image || 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&q=80'}"
           alt="${p.title}" loading="lazy">
      <div class="card-overlay"></div>
      <span class="card-badge ${badge}">${p.badge || 'Property'}</span>
      <button class="card-like ${liked ? 'liked' : ''}"
              onclick="toggleLike(event,'${p.property_id}',this)">
        <svg width="14" height="14" viewBox="0 0 24 24"
             fill="${liked ? '#FF7A00' : 'none'}"
             stroke="${liked ? '#FF7A00' : 'currentColor'}" stroke-width="2">
          <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
        </svg>
      </button>
      ${showScore ? `<div class="ai-score">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>${score}% match</div>` : ''}
    </div>
    <div class="card-body">
      <div class="card-price">${p.price_display || formatPrice(p.price)}</div>
      <div class="card-title">${p.title}</div>
      <div class="card-loc">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>${p.location}
      </div>
      <div class="card-specs">
        ${p.bedrooms > 0 ? `<div class="spec">🛏 <strong>${p.bedrooms}</strong> Beds</div>` : ''}
        ${p.size_sqft    ? `<div class="spec">📐 <strong>${p.size_sqft}</strong> sqft</div>` : ''}
        <div class="spec">🏠 <strong>${p.property_type}</strong></div>
      </div>
      <div class="card-footer">
        <button class="btn-view"
          onclick="event.stopPropagation();trackView('${p.property_id}','click');openModalData(${dataP})">
          View Details
        </button>
        <button class="btn-contact" onclick="event.stopPropagation()">Contact</button>
      </div>
    </div>
  </div>`;
}

// ─── Modal ────────────────────────────────────────────────────────────────
function openModalData(p) {
  trackView(p.property_id, 'view');
  document.getElementById('modalImage').src   = p.image || 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=800&q=80';
  document.getElementById('modalPrice').textContent  = p.price_display || formatPrice(p.price);
  document.getElementById('modalTitle').textContent  = p.title;
  document.getElementById('modalLocText').textContent = p.location;
  document.getElementById('modalSpecs').innerHTML = [
    { val: p.bedrooms > 0 ? p.bedrooms : 'N/A', key: 'Bedrooms' },
    { val: p.size_sqft ? p.size_sqft + ' sqft' : 'N/A', key: 'Size' },
    { val: p.property_type, key: 'Type' },
  ].map(s => `<div class="modal-spec"><div class="modal-spec-val">${s.val}</div><div class="modal-spec-key">${s.key}</div></div>`).join('');
  document.getElementById('modalAmenities').innerHTML =
    (p.amenities || []).map(a => `<span class="amenity-tag">${a}</span>`).join('');
  document.getElementById('modalDesc').textContent = p.description || '';
  document.getElementById('modalMeta').innerHTML = [
    { k: 'Builder', v: p.builder || '—' },
    { k: 'Possession', v: p.possession || '—' },
    { k: 'RERA', v: p.rera || 'Registered' },
    { k: 'Brokerage', v: '0%' },
  ].map(m => `<span><strong>${m.k}:</strong> ${m.v}</span>`).join('');
  document.getElementById('modalOverlay').classList.add('open');
}

function closeModal(e) {
  if (e.target === document.getElementById('modalOverlay')) closeModalDirect();
}
function closeModalDirect() {
  document.getElementById('modalOverlay').classList.remove('open');
}

// Keyboard close
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModalDirect();
});

// ─── Likes ────────────────────────────────────────────────────────────────
function toggleLike(e, propId, btn) {
  e.stopPropagation();
  const idx = likedProps.indexOf(propId);
  const svg = btn.querySelector('svg');
  if (idx === -1) {
    likedProps.push(propId);
    btn.classList.add('liked');
    svg.setAttribute('fill', '#FF7A00');
    svg.setAttribute('stroke', '#FF7A00');
    showToast('Added to wishlist ❤️', 'ok');
    trackView(propId, 'click');
  } else {
    likedProps.splice(idx, 1);
    btn.classList.remove('liked');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    showToast('Removed from wishlist', 'warn');
  }
  localStorage.setItem('bf_liked', JSON.stringify(likedProps));
}

// ─── Pagination ───────────────────────────────────────────────────────────
function renderPagination(containerId, page, pages, onPageChange) {
  const el = document.getElementById(containerId);
  if (!el || pages <= 1) { if (el) el.innerHTML = ''; return; }
  let html = '';
  if (page > 1) html += `<button class="page-btn" onclick="(${onPageChange})(${page - 1})">‹</button>`;
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - page) <= 1) {
      html += `<button class="page-btn${i === page ? ' active' : ''}" onclick="(${onPageChange})(${i})">${i}</button>`;
    } else if (Math.abs(i - page) === 2) {
      html += `<span style="color:var(--muted);padding:0 4px;line-height:36px">…</span>`;
    }
  }
  if (page < pages) html += `<button class="page-btn" onclick="(${onPageChange})(${page + 1})">›</button>`;
  el.innerHTML = html;
}

// ─── Toast ────────────────────────────────────────────────────────────────
function showToast(msg, type = 'ok') {
  const t   = document.getElementById('toast');
  const dot = document.getElementById('toastDot');
  if (!t) return;
  document.getElementById('toastMsg').textContent = msg;
  dot.style.background = type === 'error' ? 'var(--error)' : type === 'warn' ? 'var(--warn)' : 'var(--ok)';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ─── Render Grid ──────────────────────────────────────────────────────────
function renderGrid(containerId, props, showScore = false) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = props.length
    ? props.map((p, i) => propertyCard(p, i, showScore)).join('')
    : emptyState('No properties found');
}

// ─── Helpers ──────────────────────────────────────────────────────────────
function formatPrice(p) {
  if (!p) return '₹ On Request';
  if (p >= 10_000_000) return '₹' + (p / 10_000_000).toFixed(1) + ' Cr';
  if (p >= 100_000)    return '₹' + Math.floor(p / 100_000) + ' Lakh';
  return '₹' + p.toLocaleString('en-IN');
}

function getBadgeClass(badge) {
  if (!badge) return 'default';
  const b = badge.toLowerCase();
  if (b.includes('ready') || b.includes('move'))  return 'ready';
  if (b.includes('new')   || b.includes('launch')) return 'new';
  if (b.includes('luxury')|| b.includes('penthouse')) return 'luxury';
  if (b.includes('hot')   || b.includes('limited')) return 'hot';
  if (b.includes('plot'))  return 'plot';
  return 'default';
}

function emptyState(msg) {
  return `<div class="empty-state" style="grid-column:1/-1">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    </svg>
    <div>${msg}</div>
  </div>`;
}

function skeletonCard(delay = 0) {
  return `<div class="skeleton" style="animation-delay:${delay}s">
    <div class="skel-img"></div>
    <div class="skel-body">
      <div class="skel-line w80"></div>
      <div class="skel-line w60"></div>
      <div class="skel-line w40"></div>
    </div>
  </div>`;
}

function addToSearchHistory(q) {
  let h = JSON.parse(localStorage.getItem('bf_searches') || '[]');
  h.unshift(q);
  localStorage.setItem('bf_searches', JSON.stringify(h.slice(0, 20)));
}