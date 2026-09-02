/**
 * folio.js
 * "Onboard Investor" — GIFT Outbound folio creation wizard.
 * Fully self-contained front-end flow: client selection → document upload →
 * CKYC & occupation → generated application-form review → completion.
 * All client records below are fictitious placeholder data for demo purposes.
 */

document.addEventListener('DOMContentLoaded', () => {

  // --------------------------------------------------------------------------
  // Seed Data
  // --------------------------------------------------------------------------
  const CLIENTS = [
    {
      id: 1, name: 'Rohan Mehta', phone: '9821045678', email: 'rohan.mehta27@gmail.com',
      pan: 'BXTPM4521Q', dob: '14-03-1994', gender: 'Male',
      address: { line: '14, Sunview Apartments, Linking Road', city: 'Mumbai', state: 'Maharashtra', pincode: '400050' },
      bank: { account: '03810023456712', bankName: 'HDFC Bank', branch: 'Bandra West', ifsc: 'HDFC0000381' },
      nominee: { name: 'Meera Mehta', dob: '22-11-1996', relation: 'Spouse', mobile: '9821045000' },
      grossIncome: '$10,000 to $50,000',
    },
    {
      id: 2, name: 'Ananya Sharma', phone: '9910023456', email: 'ananya.sharma.blr@gmail.com',
      pan: 'CZLPS7789K', dob: '02-07-1990', gender: 'Female',
      address: { line: '221, Palm Meadows, Whitefield', city: 'Bengaluru', state: 'Karnataka', pincode: '560066' },
      bank: { account: '50100234567890', bankName: 'ICICI Bank', branch: 'Whitefield', ifsc: 'ICIC0005678' },
      nominee: { name: 'Suresh Sharma', dob: '09-01-1962', relation: 'Father', mobile: '9910099000' },
      grossIncome: '$50,000 to $100,000',
    },
    {
      id: 3, name: 'Kabir Chatterjee', phone: '9836012345', email: 'kabir.chatterjee.kol@outlook.com',
      pan: 'DPPCK3345L', dob: '19-09-1988', gender: 'Male',
      address: { line: '7B, Lake Gardens', city: 'Kolkata', state: 'West Bengal', pincode: '700045' },
      bank: { account: '20045612378901', bankName: 'Axis Bank', branch: 'Lake Gardens', ifsc: 'UTIB0002045' },
      nominee: { name: 'Rina Chatterjee', dob: '05-05-1991', relation: 'Spouse', mobile: '9836099887' },
      grossIncome: 'Above $100,000',
    },
    {
      id: 4, name: 'Isha Verma', phone: '9711234567', email: 'isha.verma.dl@gmail.com',
      pan: 'EXQPV1290M', dob: '27-12-1999', gender: 'Female',
      address: { line: 'D-45, Vasant Kunj', city: 'New Delhi', state: 'Delhi', pincode: '110070' },
      bank: { account: '11223344556677', bankName: 'Punjab National Bank', branch: 'Vasant Kunj', ifsc: 'PUNB0112200' },
      nominee: { name: 'Anil Verma', dob: '14-02-1965', relation: 'Father', mobile: '9711299887' },
      grossIncome: 'Below $10,000',
    },
    {
      id: 5, name: 'Devansh Rao', phone: '9945098765', email: 'devansh.rao.hyd@gmail.com',
      pan: 'FQZPR6654N', dob: '08-06-1985', gender: 'Male',
      address: { line: '302, Cyber Towers, Hitech City', city: 'Hyderabad', state: 'Telangana', pincode: '500081' },
      bank: { account: '67788990011223', bankName: 'State Bank of India', branch: 'Hitech City', ifsc: 'SBIN0021456' },
      nominee: { name: 'Priya Rao', dob: '30-08-1987', relation: 'Spouse', mobile: '9945011223' },
      grossIncome: '$50,000 to $100,000',
    },
    {
      id: 6, name: 'Neha Kapoor', phone: '9814567890', email: 'neha.kapoor.chd@gmail.com',
      pan: 'GRMPK9087P', dob: '11-04-1993', gender: 'Female',
      address: { line: 'House 88, Sector 21', city: 'Chandigarh', state: 'Chandigarh', pincode: '160022' },
      bank: { account: '99887766554433', bankName: 'Kotak Mahindra Bank', branch: 'Sector 17', ifsc: 'KKBK0002211' },
      nominee: { name: 'Ramesh Kapoor', dob: '19-10-1960', relation: 'Father', mobile: '9814500011' },
      grossIncome: '$10,000 to $50,000',
    },
  ];

  const OCCUPATIONS = [
    'Private Sector Service', 'Public Sector Service', 'Government Service',
    'Business', 'Professional', 'Retired', 'Housewife', 'Student',
    'Agriculturist', 'Forex Dealer', 'Others',
  ];
  const EMPLOYER_OCCUPATIONS = ['Private Sector Service', 'Public Sector Service', 'Government Service', 'Professional'];
  const BUSINESS_OCCUPATIONS = ['Business'];

  const SCHEME_NAME = "Parag Parikh IFSC – S&P 500 Fund of Fund (Direct Plan)";
  // The AMC that actually issues the application form for the selected
  // scheme — shown on the form's cover page — kept separate from the
  // distributor identity (mfAPI GIFT) shown in the Distributor row below it.
  const FUND_AMC_NAME = "PPFAS Alternate Asset Managers IFSC Private Limited";

  const SIDE_PANELS = [
    {
      theme: '',
      title: 'Invest in Global Assets <span class="text-blue-400">without the offshore complexity.</span>',
      subtitle: 'Access US equities, global ETFs, and international funds from a single GIFT City account.',
      art: `
        <svg viewBox="0 0 280 200" class="w-full max-w-[260px]" fill="none">
          <defs>
            <linearGradient id="fg1a" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#60a5fa"/><stop offset="100%" stop-color="#2563eb"/>
            </linearGradient>
          </defs>
          <circle cx="140" cy="105" r="62" stroke="url(#fg1a)" stroke-width="1.4" opacity="0.55"/>
          <ellipse cx="140" cy="105" rx="62" ry="22" stroke="#93c5fd" stroke-width="1" opacity="0.35"/>
          <ellipse cx="140" cy="105" rx="22" ry="62" stroke="#93c5fd" stroke-width="1" opacity="0.35"/>
          <circle cx="140" cy="105" r="46" fill="url(#fg1a)" opacity="0.16"/>
          <path d="M96 118 Q118 92 140 100 T184 78" stroke="#79FE0C" stroke-width="3" stroke-linecap="round" fill="none"/>
          <path d="M170 82 L184 78 L182 94" stroke="#79FE0C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <circle cx="96" cy="118" r="4" fill="#f8fafc"/>
          <circle cx="140" cy="100" r="4" fill="#f8fafc"/>
          <circle cx="184" cy="78" r="4" fill="#f8fafc"/>
          <circle cx="60" cy="60" r="2.5" fill="#93c5fd"/>
          <circle cx="220" cy="150" r="2.5" fill="#93c5fd"/>
          <circle cx="210" cy="55" r="2" fill="#79FE0C"/>
          <circle cx="55" cy="150" r="2" fill="#79FE0C"/>
        </svg>
      `,
    },
    {
      theme: 'side-warm',
      title: 'Overcome <span class="text-amber-300">Domestic Investment Limits.</span>',
      subtitle: 'GIFT City lets qualified investors allocate up to $250,000 every year, legally and seamlessly.',
      art: `
        <svg viewBox="0 0 280 200" class="w-full max-w-[260px]" fill="none">
          <defs>
            <linearGradient id="fg2a" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#fde68a"/>
            </linearGradient>
          </defs>
          <rect x="48" y="118" width="28" height="52" rx="4" fill="url(#fg2a)" opacity="0.85"/>
          <rect x="90" y="94" width="28" height="76" rx="4" fill="url(#fg2a)" opacity="0.9"/>
          <rect x="132" y="70" width="28" height="100" rx="4" fill="url(#fg2a)" opacity="0.95"/>
          <rect x="174" y="42" width="28" height="128" rx="4" fill="url(#fg2a)"/>
          <path d="M48 108 L90 84 L132 60 L174 32" stroke="#fef3c7" stroke-width="2" stroke-linecap="round" stroke-dasharray="1 7"/>
          <circle cx="215" cy="60" r="22" fill="#2b1608" stroke="#fbbf24" stroke-width="2"/>
          <text x="215" y="67" text-anchor="middle" font-size="20" font-weight="800" fill="#fbbf24" font-family="var(--font-sans)">$</text>
        </svg>
      `,
    },
    {
      theme: 'side-purple',
      title: 'International Diversification, <span class="text-indigo-300">always stay on top.</span>',
      subtitle: 'Global benchmarks have historically outpaced domestic ones over the long run — diversify beyond borders.',
      art: `
        <svg viewBox="0 0 280 200" class="w-full max-w-[260px]" fill="none">
          <rect x="60" y="120" width="46" height="50" rx="6" fill="#1e1b4b" stroke="#6366f1" stroke-width="1.5"/>
          <rect x="66" y="128" width="34" height="8" fill="#ff9933"/>
          <rect x="66" y="136" width="34" height="8" fill="#f8fafc"/>
          <rect x="66" y="144" width="34" height="8" fill="#138808"/>
          <circle cx="83" cy="140" r="3.2" fill="none" stroke="#0b0f19" stroke-width="1"/>

          <rect x="150" y="100" width="46" height="70" rx="6" fill="#1e1b4b" stroke="#818cf8" stroke-width="1.5"/>
          <rect x="156" y="108" width="34" height="54" fill="#1d3f91"/>
          <g fill="#f8fafc">
            <circle cx="162" cy="114" r="1.6"/><circle cx="168" cy="114" r="1.6"/><circle cx="174" cy="114" r="1.6"/>
            <circle cx="162" cy="120" r="1.6"/><circle cx="168" cy="120" r="1.6"/><circle cx="174" cy="120" r="1.6"/>
            <circle cx="162" cy="126" r="1.6"/><circle cx="168" cy="126" r="1.6"/>
          </g>
          <rect x="156" y="132" width="34" height="4" fill="#dc2626"/>
          <rect x="156" y="140" width="34" height="4" fill="#f8fafc"/>
          <rect x="156" y="148" width="34" height="4" fill="#dc2626"/>
          <rect x="156" y="156" width="34" height="4" fill="#f8fafc"/>

          <path d="M40 178 H216" stroke="#4338ca" stroke-width="2" opacity="0.5"/>
          <path d="M110 96 Q150 60 190 40" stroke="#a5b4fc" stroke-width="2.5" stroke-linecap="round" fill="none"/>
          <path d="M176 44 L190 40 L186 54" stroke="#a5b4fc" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
      `,
    },
  ];

  // --------------------------------------------------------------------------
  // State
  // --------------------------------------------------------------------------
  const fstate = {
    step: 0, // 0 select client, 1 documents, 2 ckyc/occupation, 3 review, 4 completed
    clientId: null,
    search: '',
    documents: { aadhaar: null, pan: null, bank: null },
    ckyc: '',
    occupation: '',
    employerName: '',
    placeOfWork: '',
    businessName: '',
    businessNature: '',
    signHours: 3,
    signMethod: null, // 'inapp' | 'mail'
  };

  // Object URLs for previewing uploaded image documents in the Review step
  // and the generated PDF. Keyed the same way as fstate.documents.
  const docPreviewUrls = { aadhaar: null, pan: null, bank: null };

  const modal = document.getElementById('folioModal');
  const sidePanel = document.getElementById('folioSidePanel');
  const sideTitle = document.getElementById('folioSideTitle');
  const sideSubtitle = document.getElementById('folioSideSubtitle');
  const sideArt = document.getElementById('folioSideArt');
  const stepBody = document.getElementById('folioStepBody');
  const backBtn = document.getElementById('folioBackBtn');
  const nextBtn = document.getElementById('folioNextBtn');
  const nextLabel = document.getElementById('folioNextLabel');
  const footerNav = document.getElementById('folioFooterNav');

  if (!modal) return;

  function getClient() {
    return CLIENTS.find(c => c.id === fstate.clientId) || null;
  }

  function resetFlow() {
    fstate.step = 0;
    fstate.clientId = null;
    fstate.search = '';
    fstate.documents = { aadhaar: null, pan: null, bank: null };
    fstate.ckyc = '';
    fstate.occupation = '';
    fstate.employerName = '';
    fstate.placeOfWork = '';
    fstate.businessName = '';
    fstate.businessNature = '';
    fstate.signHours = 2 + Math.floor(Math.random() * 3);
    fstate.signMethod = null;
    Object.values(docPreviewUrls).forEach(url => { if (url) URL.revokeObjectURL(url); });
    docPreviewUrls.aadhaar = null;
    docPreviewUrls.pan = null;
    docPreviewUrls.bank = null;
  }

  function openModal() {
    resetFlow();
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    render();
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }

  // --------------------------------------------------------------------------
  // Progress + Side Panel
  // --------------------------------------------------------------------------
  function updateProgress() {
    const segs = document.querySelectorAll('.folio-progress-seg');
    segs.forEach((seg, idx) => {
      seg.classList.remove('done', 'active');
      if (fstate.step > idx || fstate.step === 4) seg.classList.add('done');
      else if (fstate.step === idx) seg.classList.add('active');
    });
  }

  function updateSidePanel() {
    const panelIdx = Math.min(fstate.step, 3) % SIDE_PANELS.length;
    const panel = SIDE_PANELS[panelIdx];
    sidePanel.classList.remove('side-warm', 'side-purple');
    if (panel.theme) sidePanel.classList.add(panel.theme);
    sideTitle.innerHTML = panel.title;
    sideSubtitle.textContent = panel.subtitle;
    if (sideArt) sideArt.innerHTML = panel.art || '';
  }

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function initials(name) {
    return name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
  }

  function renderBoxes(text, minBoxes) {
    const chars = String(text || '').toUpperCase().split('');
    const count = Math.max(chars.length, minBoxes || 0);
    let html = '<span class="doc-boxes">';
    for (let i = 0; i < count; i++) {
      html += `<span class="doc-box">${chars[i] ? escapeHtml(chars[i]) : ''}</span>`;
    }
    html += '</span>';
    return html;
  }

  function todayFormatted() {
    const d = new Date();
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}${mm}${yyyy}`;
  }

  // --------------------------------------------------------------------------
  // Step Renderers
  // --------------------------------------------------------------------------
  function renderStepClient() {
    const filtered = CLIENTS.filter(c => {
      const q = fstate.search.trim().toLowerCase();
      if (!q) return true;
      return c.name.toLowerCase().includes(q) || c.phone.includes(q);
    });

    stepBody.innerHTML = `
      <h3 class="text-lg font-black text-[var(--color-text)] mb-1">Select client for <span class="text-blue-500">GIFT Outbound</span></h3>
      <div class="flex flex-wrap items-center gap-2 mb-4 mt-3">
        <span class="folio-fund-chip live">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Live · Parag Parikh
        </span>
        <span class="folio-fund-chip">Coming soon · Edelweiss</span>
        <span class="folio-fund-chip">Coming soon · DSP</span>
      </div>
      <div class="relative mb-3">
        <input type="text" id="folioClientSearch" placeholder="Search for clients by name or mobile..." value="${escapeHtml(fstate.search)}"
          class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl pl-9 pr-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500" />
        <svg class="w-4 h-4 absolute left-3 top-3 text-[var(--color-text-subtle)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      </div>
      <div class="space-y-1 max-h-64 overflow-y-auto pr-1">
        ${filtered.map(c => `
          <div class="folio-client-row ${fstate.clientId === c.id ? 'selected' : ''}" data-client-id="${c.id}">
            <div class="folio-client-avatar">${initials(c.name)}</div>
            <div class="min-w-0">
              <div class="text-xs font-bold text-[var(--color-text)] truncate">${escapeHtml(c.name)}</div>
              <div class="text-[11px] text-[var(--color-text-subtle)]">+91 ${c.phone}</div>
            </div>
            ${fstate.clientId === c.id ? `<svg class="w-4 h-4 ml-auto text-blue-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>` : ''}
          </div>
        `).join('') || `<div class="text-xs text-[var(--color-text-subtle)] py-6 text-center">No clients matched your search.</div>`}
      </div>
    `;

    document.getElementById('folioClientSearch').addEventListener('input', (e) => {
      fstate.search = e.target.value;
      renderStepClient();
    });

    stepBody.querySelectorAll('.folio-client-row').forEach(row => {
      row.addEventListener('click', () => {
        fstate.clientId = Number(row.getAttribute('data-client-id'));
        renderStepClient();
        updateFooter();
      });
    });
  }

  function renderStepDocuments() {
    const client = getClient();
    const bankLabel = client ? `${client.bank.bankName} •${client.bank.account.slice(-4)}` : 'your registered bank';

    const rows = [
      { key: 'aadhaar', label: 'Masked Aadhaar', desc: 'The first 8 digits are blacked out and the last 4 digits are visible.' },
      { key: 'pan', label: 'PAN Card', desc: 'A clear photo or scan of the PAN card.' },
      { key: 'bank', label: 'Bank Proof', desc: `Passbook, bank statement, or cancelled cheque of ${bankLabel}` },
    ];

    stepBody.innerHTML = `
      <h3 class="text-lg font-black text-[var(--color-text)] mb-1">Upload <span class="text-blue-500">Documents</span></h3>
      <p class="text-xs text-[var(--color-text-muted)] mb-4">Onboarding <strong class="text-[var(--color-text)]">${client ? escapeHtml(client.name) : ''}</strong> for GIFT Outbound.</p>
      <div class="space-y-4">
        ${rows.map(r => `
          <div>
            <span class="text-xs font-bold text-[var(--color-text)] block mb-0.5">${r.label}</span>
            <span class="text-[10.5px] text-[var(--color-text-subtle)] block mb-1.5">${escapeHtml(r.desc)}</span>
            <label class="folio-upload-zone ${fstate.documents[r.key] ? 'filled' : ''}" data-doc-key="${r.key}">
              <span class="flex items-center gap-2 min-w-0">
                <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                <span class="truncate">${fstate.documents[r.key] ? escapeHtml(fstate.documents[r.key].name) : 'Upload file — jpg, png, or pdf (max 5mb)'}</span>
              </span>
              ${fstate.documents[r.key] ? `<button type="button" class="folio-remove-doc text-[var(--color-text-subtle)] hover:text-red-400 shrink-0" data-doc-key="${r.key}">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>` : ''}
              <input type="file" class="hidden folio-file-input" data-doc-key="${r.key}" accept=".jpg,.jpeg,.png,.pdf" />
            </label>
          </div>
        `).join('')}
      </div>
    `;

    stepBody.querySelectorAll('.folio-file-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const key = input.getAttribute('data-doc-key');
        const file = e.target.files && e.target.files[0];
        if (file) {
          fstate.documents[key] = { name: file.name, type: file.type, file };
          if (docPreviewUrls[key]) URL.revokeObjectURL(docPreviewUrls[key]);
          docPreviewUrls[key] = file.type.startsWith('image/') ? URL.createObjectURL(file) : null;
          renderStepDocuments();
          updateFooter();
        }
      });
    });

    stepBody.querySelectorAll('.folio-remove-doc').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const key = btn.getAttribute('data-doc-key');
        fstate.documents[key] = null;
        if (docPreviewUrls[key]) { URL.revokeObjectURL(docPreviewUrls[key]); docPreviewUrls[key] = null; }
        renderStepDocuments();
        updateFooter();
      });
    });
  }

  function renderStepCkyc() {
    const showEmployer = EMPLOYER_OCCUPATIONS.includes(fstate.occupation);
    const showBusiness = BUSINESS_OCCUPATIONS.includes(fstate.occupation);

    stepBody.innerHTML = `
      <h3 class="text-lg font-black text-[var(--color-text)] mb-4"><span class="text-blue-500">CKYC</span> &amp; Occupation</h3>

      <label class="text-xs font-bold text-[var(--color-text)] block mb-1">CKYC</label>
      <p class="text-[10.5px] text-[var(--color-text-subtle)] mb-1.5">Central Know Your Customer number issued by CERSAI. <a href="https://www.ckycindia.in/" target="_blank" rel="noopener noreferrer" class="text-blue-400 font-bold hover:underline" id="folioCkycHelp">How to find yours? ↗</a></p>
      <input type="text" id="folioCkycInput" maxlength="14" inputmode="numeric" placeholder="Enter your 14 digit CKYC number" value="${escapeHtml(fstate.ckyc)}"
        class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500 font-mono tracking-wider mb-1" />
      <p id="folioCkycCounter" class="text-[10px] text-[var(--color-text-subtle)] mb-4">${fstate.ckyc.length}/14 digits</p>

      <label class="text-xs font-bold text-[var(--color-text)] block mb-1.5">Occupation</label>
      <select id="folioOccupationSelect" class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] focus:outline-none focus:border-blue-500 mb-4">
        <option value="">Select occupation</option>
        ${OCCUPATIONS.map(o => `<option value="${o}" ${fstate.occupation === o ? 'selected' : ''}>${o}</option>`).join('')}
      </select>

      ${showEmployer ? `
        <div class="grid grid-cols-1 gap-3 mb-2">
          <div>
            <label class="text-xs font-bold text-[var(--color-text)] block mb-1">Name of Employer</label>
            <input type="text" id="folioEmployerInput" placeholder="e.g. Company / organisation name" value="${escapeHtml(fstate.employerName)}"
              class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="text-xs font-bold text-[var(--color-text)] block mb-1">Place of Work</label>
            <input type="text" id="folioPlaceInput" placeholder="e.g. City" value="${escapeHtml(fstate.placeOfWork)}"
              class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500" />
          </div>
        </div>
      ` : ''}

      ${showBusiness ? `
        <div class="grid grid-cols-1 gap-3 mb-2">
          <div>
            <label class="text-xs font-bold text-[var(--color-text)] block mb-1">Name of Business</label>
            <input type="text" id="folioBusinessNameInput" placeholder="e.g. Business / firm name" value="${escapeHtml(fstate.businessName)}"
              class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="text-xs font-bold text-[var(--color-text)] block mb-1">Nature of Business</label>
            <input type="text" id="folioBusinessNatureInput" placeholder="e.g. Trading, Consulting..." value="${escapeHtml(fstate.businessNature)}"
              class="w-full bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-xl px-3 py-2.5 text-xs text-[var(--color-text)] placeholder-[var(--color-text-subtle)] focus:outline-none focus:border-blue-500" />
          </div>
        </div>
      ` : ''}
    `;

    const ckycInput = document.getElementById('folioCkycInput');
    ckycInput.addEventListener('input', (e) => {
      fstate.ckyc = e.target.value.replace(/\D/g, '').slice(0, 14);
      e.target.value = fstate.ckyc;
      document.getElementById('folioCkycCounter').textContent = `${fstate.ckyc.length}/14 digits`;
      updateFooter();
    });


    document.getElementById('folioOccupationSelect').addEventListener('change', (e) => {
      fstate.occupation = e.target.value;
      if (!EMPLOYER_OCCUPATIONS.includes(fstate.occupation)) { fstate.employerName = ''; fstate.placeOfWork = ''; }
      if (!BUSINESS_OCCUPATIONS.includes(fstate.occupation)) { fstate.businessName = ''; fstate.businessNature = ''; }
      renderStepCkyc();
      updateFooter();
    });

    const employerInput = document.getElementById('folioEmployerInput');
    if (employerInput) employerInput.addEventListener('input', (e) => { fstate.employerName = e.target.value; updateFooter(); });
    const placeInput = document.getElementById('folioPlaceInput');
    if (placeInput) placeInput.addEventListener('input', (e) => { fstate.placeOfWork = e.target.value; updateFooter(); });
    const bizNameInput = document.getElementById('folioBusinessNameInput');
    if (bizNameInput) bizNameInput.addEventListener('input', (e) => { fstate.businessName = e.target.value; updateFooter(); });
    const bizNatureInput = document.getElementById('folioBusinessNatureInput');
    if (bizNatureInput) bizNatureInput.addEventListener('input', (e) => { fstate.businessNature = e.target.value; updateFooter(); });
  }

  function renderStepReview() {
    const c = getClient();
    if (!c) return;

    const occChecks = OCCUPATIONS.map(o => `
      <div><span class="doc-check ${fstate.occupation === o ? 'checked' : ''}">${fstate.occupation === o ? '✓' : ''}</span>${o}</div>
    `).join('');

    const incomeOptions = ['Below $10,000', '$10,000 to $50,000', '$50,000 to $100,000', 'Above $100,000'];
    const incomeChecks = incomeOptions.map(i => `
      <div><span class="doc-check ${c.grossIncome === i ? 'checked' : ''}">${c.grossIncome === i ? '✓' : ''}</span>${i}</div>
    `).join('');

    const showEmployer = EMPLOYER_OCCUPATIONS.includes(fstate.occupation);
    const showBusiness = BUSINESS_OCCUPATIONS.includes(fstate.occupation);

    const docRows = [
      { key: 'aadhaar', label: 'Masked Aadhaar' },
      { key: 'pan', label: 'PAN Card' },
      { key: 'bank', label: 'Bank Proof' },
    ];
    const allDocsUploaded = docRows.every(r => fstate.documents[r.key]);

    const thumbHtml = docRows.map(r => {
      const doc = fstate.documents[r.key];
      const url = docPreviewUrls[r.key];
      const preview = doc
        ? (url
            ? `<img src="${url}" alt="${escapeHtml(r.label)}" />`
            : `<svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>`)
        : `<span class="text-[8px] text-slate-400">Not uploaded</span>`;
      return `
        <div class="doc-thumb">
          <div class="doc-thumb-preview">${preview}</div>
          <div class="doc-thumb-label">${escapeHtml(r.label)}${doc ? '' : ' — missing'}</div>
        </div>`;
    }).join('');

    stepBody.innerHTML = `
      <div class="flex items-start justify-between gap-3 mb-1">
        <h3 class="text-lg font-black text-[var(--color-text)]">Review</h3>
        <button id="folioDownloadPdfBtn" type="button" class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-blue-400 hover:border-blue-500/40 bg-[var(--color-card)] transition-all">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          <span id="folioDownloadPdfLabel">Download PDF</span>
        </button>
      </div>
      <p class="text-xs text-[var(--color-text-muted)] mb-3">Confirm the generated application form before sending it for e-signature. Scroll through — it's paginated the same way the printed form is.</p>
      <div class="folio-doc p-3 max-h-[420px] overflow-y-auto">

        <div class="doc-page">
          <div class="doc-title-box">
            <div class="doc-title-line">${escapeHtml(FUND_AMC_NAME)}</div>
            <div class="doc-title-line">Application Form for Outbound Funds</div>
            <div class="doc-title-line">(Individual)</div>
            <div class="doc-title-scheme">Scheme Applied For: ${escapeHtml(SCHEME_NAME)}</div>
          </div>

          <div class="doc-plain-title">Checklist for Individuals</div>
          <p class="text-[8.5px] text-slate-600 mb-1" style="text-decoration:underline;">For Individual/ Joint holder/ Minor</p>
          <table class="mb-1">
            <tr><th style="width:16%">Sr. No.</th><th>Description</th><th style="width:12%">Check Box</th></tr>
            <tr>
              <td>1.</td>
              <td>Documentation</td>
              <td><span class="doc-check ${allDocsUploaded ? 'checked' : ''}">${allDocsUploaded ? '✓' : ''}</span></td>
            </tr>
            <tr>
              <td rowspan="1">For individual/ joint holders</td>
              <td>
                Self-attested copies of identity proof &amp; address proof of individual/ joint holders.
                <ol style="padding-left:14px;margin:2px 0 0;">
                  <li>Copy of PAN Card</li>
                  <li>Copy of Address Proof</li>
                </ol>
                <span class="text-slate-400" style="font-style:italic;">(If correspondence address and permanent address are different, then proof of address to be provided for both addresses)</span>
              </td>
              <td>
                <div class="flex flex-col gap-1">
                  <span class="doc-check ${fstate.documents.pan ? 'checked' : ''}">${fstate.documents.pan ? '✓' : ''}</span>
                  <span class="doc-check ${fstate.documents.aadhaar ? 'checked' : ''}">${fstate.documents.aadhaar ? '✓' : ''}</span>
                </div>
              </td>
            </tr>
            <tr>
              <td>For Minor</td>
              <td>
                <div>Age proof of minor (Birth certificate or school certificate) attested by the guardian</div>
              </td>
              <td><span class="doc-check"></span></td>
            </tr>
            <tr>
              <td></td>
              <td>Copies of PAN Card &amp; address proof of minor attested by guardian</td>
              <td><span class="doc-check"></span></td>
            </tr>
            <tr>
              <td></td>
              <td>Self-attested copy of PAN Card &amp; address proof of guardian</td>
              <td><span class="doc-check"></span></td>
            </tr>
            <tr>
              <td></td>
              <td>Photograph of both minor and Guardian to be affixed in the Application Form</td>
              <td><span class="doc-check"></span></td>
            </tr>
            <tr>
              <td>Acceptable Address Proofs</td>
              <td class="text-[8px]">Copy of Masked Aadhaar Card or Passport or Driving License or copy of utility bill (not more than two months old), property/ municipal tax receipt, Post Office savings bank account statement or statement of a bank account, letter of allotment of accommodation from employer issued by State Government or Central Government departments, statutory or regulatory bodies, public sector undertakings, scheduled commercial banks, financial institutions and listed companies and leave and license agreements with such employers allotting official accommodation</td>
              <td></td>
            </tr>
            <tr>
              <td rowspan="2">Bank Details</td>
              <td>Proof: Cancelled cheque leaf for registered bank/ bank statement (not more than 2 months old) <span style="font-style:italic;">(should be personalised and bearing the name of the Investor)</span></td>
              <td><span class="doc-check ${fstate.documents.bank ? 'checked' : ''}">${fstate.documents.bank ? '✓' : ''}</span></td>
            </tr>
            <tr>
              <td class="text-[8px]">Bank Details for International Bank Accounts should be as per any global Fund format capturing details for 3 segments: Beneficiary, Correspondent Bank, Intermediary Bank. Along with SWIFT/BIC code</td>
              <td></td>
            </tr>
            <tr>
              <td>2.</td>
              <td>CERSAI Form if CKYC is not done and KIN is not available</td>
              <td><span class="doc-check ${fstate.ckyc ? '' : 'checked'}">${fstate.ckyc ? '' : '✓'}</span></td>
            </tr>
          </table>
          <p class="text-[8px] text-slate-500 leading-relaxed">In case of joint Investors, please provide the KYC documents for each Investor and full signature and initial is to be done by each Investor. Documents to be signed by the Guardian on behalf of minor.</p>

          <table class="mb-2 mt-2">
            <tr>
              <th style="width:25%">Distributor</th><th style="width:25%">Code</th><th style="width:30%">Email</th><th style="width:20%">Mobile</th>
            </tr>
            <tr>
              <td>mfAPI GIFT</td><td>GC100450</td><td>onboarding@mfapigift.in</td><td>9999900000</td>
            </tr>
          </table>

          <div class="doc-brand-mark">
            <svg viewBox="0 0 40 40" width="30" height="30"><circle cx="20" cy="20" r="18" fill="#0f172a"/><path d="M20 8c6 4 9 8 9 13a9 9 0 11-18 0c0-5 3-9 9-13z" fill="#22c55e"/><circle cx="20" cy="23" r="3.4" fill="#0f172a"/></svg>
            <span>
              <span class="doc-brand-mark-top">mfAPI</span>
              <span class="doc-brand-mark-bottom">GIFT</span>
            </span>
          </div>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">I &nbsp; General Information</div>
          <table class="mb-2">
            <tr><td colspan="2">
              <span class="doc-field-label">Name of Sole / First Applicant (as per PAN)</span>
              ${renderBoxes(c.name, 26)}
            </td></tr>
            <tr>
              <td style="width:60%">
                <span class="doc-field-label">Date of Birth</span>${renderBoxes(c.dob.replace(/-/g, ''), 8)}
                <span class="ml-3">
                  <span class="doc-check ${c.gender === 'Male' ? 'checked' : ''}">${c.gender === 'Male' ? '✓' : ''}</span>Male
                  &nbsp;
                  <span class="doc-check ${c.gender === 'Female' ? 'checked' : ''}">${c.gender === 'Female' ? '✓' : ''}</span>Female
                </span>
              </td>
              <td>
                <span class="doc-field-label">PAN</span>${renderBoxes(c.pan, 10)}
              </td>
            </tr>
            <tr><td colspan="2">
              <span class="doc-field-label">CKYC – KIN (as entered during onboarding)</span>
              ${renderBoxes(fstate.ckyc, 14)}
            </td></tr>
            <tr><td colspan="2">
              <span class="doc-check checked">✓</span> Single &nbsp;&nbsp; <span class="doc-check"></span> Joint &nbsp;&nbsp; <span class="doc-check"></span> Minor &nbsp; <span class="text-slate-400 text-[9px]">(Mode of Operation)</span>
            </td></tr>
            <tr><td colspan="2">
              <span class="doc-field-label">Correspondence &amp; Permanent Address</span>
              ${escapeHtml(c.address.line)}, ${escapeHtml(c.address.city)}, ${escapeHtml(c.address.state)} – ${escapeHtml(c.address.pincode)}, India
            </td></tr>
            <tr>
              <td><span class="doc-field-label">Mobile No.</span>${renderBoxes(c.phone, 10)}</td>
              <td><span class="doc-field-label">Email ID</span>${escapeHtml(c.email)}</td>
            </tr>
          </table>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">II &nbsp; KYC Details</div>
          <table class="mb-2">
            <tr><th style="width:20%">Categories</th><th>Sole/First Applicant/Guardian</th><th>Second Applicant</th><th>Third Applicant</th></tr>
            <tr>
              <td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Occupation</td>
              <td><div class="grid grid-cols-2 gap-x-2 gap-y-0.5">${occChecks}</div></td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
            </tr>
            <tr>
              <td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Gross Annual Income</td>
              <td><div class="grid grid-cols-1 gap-y-0.5">${incomeChecks}</div></td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
            </tr>
            <tr>
              <td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">PEP Disclosure</td>
              <td><span class="doc-check checked">✓</span> Not a Politically Exposed Person</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
            </tr>
            <tr>
              <td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">In case of Salaried</td>
              <td>${showEmployer ? `Name of Employer: ${escapeHtml(fstate.employerName) || '—'}<br/>Place of Work: ${escapeHtml(fstate.placeOfWork) || '—'}` : '<span class="text-slate-400">—</span>'}</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
            </tr>
            <tr>
              <td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">In case Occupation stated as Business</td>
              <td>${showBusiness ? `Name of Business: ${escapeHtml(fstate.businessName) || '—'}<br/>Nature of Business: ${escapeHtml(fstate.businessNature) || '—'}` : '<span class="text-slate-400">—</span>'}</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
              <td class="text-slate-400 text-[8.5px]">Not Applicable</td>
            </tr>
          </table>

          <div class="doc-section-title">III &nbsp; Foreign Account Tax Compliance Act (FATCA) &amp; CRS Details</div>
          <table class="mb-2">
            <tr><th style="width:20%">Categories</th><th>Sole/First Applicant/Guardian</th><th>Second Applicant</th><th>Third Applicant</th></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Country of Birth</td><td><span class="doc-check checked">✓</span> India &nbsp; <span class="doc-check"></span> Others</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td colspan="4" class="text-center" style="font-size:9px;">Place of Birth: <strong>INDIA</strong></td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Citizenship/ Nationality</td><td><span class="doc-check checked">✓</span> Indian &nbsp; <span class="doc-check"></span> Others</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Are you also a Resident of any other country(ies) for Tax Purposes?</td><td><span class="doc-check checked">✓</span> No &nbsp; <span class="doc-check"></span> Yes</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">US Person</td><td><span class="doc-check checked">✓</span> No &nbsp; <span class="doc-check"></span> Yes</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">Country of Tax Residency 1</td><td class="text-slate-400 text-[8.5px]">Not applicable — resident Indian only</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">TIN 1 / Identification Type 1</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
            <tr><td class="doc-field-label" style="text-transform:none;font-size:9px;color:#334155;">If TIN not available, Reason</td><td><span class="doc-check"></span> A &nbsp; <span class="doc-check"></span> B &nbsp; <span class="doc-check"></span> C</td><td class="text-slate-400 text-[8.5px]">—</td><td class="text-slate-400 text-[8.5px]">—</td></tr>
          </table>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">IV &nbsp; Bank Account Details</div>
          <p class="text-[8px] text-slate-500 mb-1">Attach copy of cheque leaf/ Bank Statement/ Bank Passbook (Not older than 2 months)</p>
          <table class="mb-2">
            <tr><td colspan="2">
              <span class="doc-field-label">Account Number/IBAN</span>${renderBoxes(c.bank.account, 16)}
            </td></tr>
            <tr>
              <td>
                <span class="doc-check checked">✓</span> Savings &nbsp; <span class="doc-check"></span> Current &nbsp; <span class="doc-check"></span> RFC &nbsp; <span class="doc-check"></span> FCA (GIFT CITY) &nbsp; <span class="doc-check"></span> Others (Please Specify) ____________
              </td>
              <td><span class="doc-field-label">IFSC Code</span>${renderBoxes(c.bank.ifsc, 11)}</td>
            </tr>
            <tr>
              <td><span class="doc-field-label">Name of Bank / Branch</span>${escapeHtml(c.bank.bankName)}, ${escapeHtml(c.bank.branch)}</td>
              <td><span class="doc-field-label">SWIFT Code</span>${renderBoxes('', 11)}</td>
            </tr>
            <tr><td colspan="2"><span class="doc-field-label">Address</span>${escapeHtml(c.address.line)}, ${escapeHtml(c.address.city)}, ${escapeHtml(c.address.state)} – ${escapeHtml(c.address.pincode)}</td></tr>
            <tr><td colspan="2"><span class="doc-field-label">Correspondent Bank/ Intermediate Bank &amp; Branch Name*</span><span class="text-slate-400 text-[8.5px]">—</span></td></tr>
            <tr><td colspan="2"><span class="doc-field-label">Correspondent Bank/ Intermediate Bank SWIFT Code*</span><span class="text-slate-400 text-[8.5px]">—</span></td></tr>
          </table>
          <p class="text-[7.5px] text-slate-400 mb-2">*Mandatory for International Bank Account</p>

          <div class="doc-section-title">V &nbsp; Bank Account Details (In case Redemption Account is different)</div>
          <p class="text-[8px] text-slate-500 mb-1">Attach copy of cheque leaf/ Bank Statement/ Bank Passbook (Not older than 2 months)</p>
          <table class="mb-2">
            <tr><td colspan="2"><span class="doc-field-label">Account Number/IBAN</span><span class="text-slate-400 text-[8.5px]">Not applicable — redemption proceeds go to the account registered above</span></td></tr>
            <tr>
              <td><span class="doc-check"></span> Savings &nbsp; <span class="doc-check"></span> Current &nbsp; <span class="doc-check"></span> RFC &nbsp; <span class="doc-check"></span> FCA (GIFT CITY) &nbsp; <span class="doc-check"></span> Others (Please Specify) ____________</td>
              <td><span class="doc-field-label">Name of Bank / Branch</span><span class="text-slate-400 text-[8.5px]">—</span></td>
            </tr>
          </table>
          <p class="text-[7.5px] text-slate-400 mb-2">*Mandatory for International Bank Account</p>

          <div class="doc-section-title">VI &nbsp; Nomination Details</div>
          <table class="mb-2">
            <tr>
              <th style="width:5%">Sr No</th><th>Nominee Name</th><th>Date of Birth</th><th style="width:9%">Share of Nominee %</th><th>Identity Number</th><th>Mobile No. and Email ID</th><th>Guardian Name &amp; Relationship (In case Nominee is Minor)</th><th>Nominee/Guardian Signature</th>
            </tr>
            <tr>
              <td>1</td>
              <td>${escapeHtml(c.nominee.name)}</td>
              <td>${escapeHtml(c.nominee.dob)}</td>
              <td>100</td>
              <td class="text-[8px]">Aadhaar/PAN on file</td>
              <td>${escapeHtml(c.nominee.mobile)}</td>
              <td>${escapeHtml(c.nominee.relation)}</td>
              <td></td>
            </tr>
            <tr><td>2</td><td colspan="7" class="text-slate-400">—</td></tr>
            <tr><td>3</td><td colspan="7" class="text-slate-400">—</td></tr>
          </table>
          <p class="text-[7.5px] text-slate-500 leading-relaxed">*Share of nominee: if % is not specified, then the assets shall be distributed equally amongst all the nominees. #Identity number: Provide only number: PAN or driving license or Aadhaar (last 4 digits). Passport number (in case of NRI/OCI/PIO). Copy of the document is not required.</p>
          <table class="mt-1">
            <tr><td><span class="doc-check"></span> <strong>OPT OUT Declaration:</strong> I/We hereby confirm that I/We do not wish to appoint any nominee for my/our units held in my/our folio, and understand the issues involved in non-appointment of nominee(s) and further am/are aware that in case of death of all account holders, my/our legal heirs would need to submit all the requisite documents issued by Court or other such competent authority based on the value of assets held in the folio.</td></tr>
          </table>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">VII &nbsp; Declarations and Signature(s)</div>
          <table class="mb-2">
            <tr>
              <td class="text-[9px] text-slate-600 leading-relaxed">
                <p class="mb-1.5">I/We hereby declare and certify that all the information and particulars given by me/us in this application form are true, complete and accurate. I/We agree to immediately inform mfAPI GIFT and ${escapeHtml(FUND_AMC_NAME)} ("the FME") if there is any change in any of the information given in this Application Form. I/We confirm that the funds invested through this Application Form and any other details and documents provided post Application Form belong to me/us, and I/we have neither received nor been induced by any rebate or gifts, directly or indirectly, in making this investment.</p>
                <p class="mb-1.5">I/We also authorise such further information as the FME, or any regulatory authority may require or pursuant to any law, regulation, or direction of any regulatory authority, order/decree/award of any court/tribunal from me/us in relation to the holdings of Units of the Schemes, and further due diligence to be undertaken and I/we shall have the right to return funds and not allot Units and report the same to the applicable regulators. I/We understand that there is no assurance on the returns of the Schemes.</p>
                <p class="mb-1.5">I/We understand that if I/we are categorised as high risk investors as per the policies/procedures adopted by the FME, additional documents/declarations may be sought, in absence of which my/our application may be put on hold.</p>
                <p class="mb-1.5">I/We declare and confirm that the investment complies with the provisions of the IFSCA, the Reserve Bank of India (RBI) and Government of India rules, regulations, directions and guidelines issued thereunder by the RBI, and the Foreign Exchange Management Act, 1999 (FEMA Act) and the Foreign Exchange Management (Overseas Investment) Rules/Regulations, 2022, as amended from time to time. I/We confirm that the source of funds for the proposed investment is through permissible means and that this investment does not involve any contravention of FEMA and other applicable disclosure requirements. I/We undertake to comply with all reporting/filings, including but not limited to Form FC, Form ODI, Form FLA and Annual Performance Reports (APR), as applicable, and that the proposed investment is within the overall limit prescribed by the RBI from time to time.</p>
                <p class="mb-1.5">I/We hereby accord my/our consent to the FME/Schemes for collecting, receiving, possessing, storing, dealing, handling or disclosure of my/our personal data and authorise disclosure to any third party or agency acting in a lawful contract with the FME, for utilising the same folio number and other relevant information for all future eligible transactions. I/We hereby grant my/our consent to be contacted for all communications/reports relating to this investment on all email addresses and mobile numbers specified in this form.</p>
                <p class="mb-1.5">I/We agree and accept that the FME, their authorised agents, representatives, distributors, settlor, trustee, their employees, service providers and representatives (Authorised Parties) are not liable or responsible for any losses, costs, damages arising out of any actions undertaken or as a consequence of this investment or activities performed by them on the basis of the information provided by me/us as also due to any not intimating/ delay in intimating such changes.</p>
                <p class="mb-1.5">I/We hereby accord my/our consent to the FME to disclose, share, remit in any form, mode or manner, all/ any of the information provided by me to the Authorised Parties along with any change/ modification to the above information as and when required by any regulatory or judicial authorities/ agencies including Financial Intelligence Unit-India (FIU-IND), the Authorised Dealer or other regulatory or judicial authorities, without any obligation of advising me/us of the same.</p>
                <p class="mb-1.5">I/We hereby accord my/our consent to mfAPI GIFT and ${escapeHtml(FUND_AMC_NAME)} for receiving promotional material/information relating to this and other schemes via email, SMS, or telemarketing calls on the mobile number and email address provided by me/us in this Application Form. mfAPI GIFT reserves the right to inform the existing Distributor/ Referral Agent of any request received from investors which can directly or indirectly impact the distributor's/ referral agent's interest. I/We have read, understood, and agree to the terms and conditions mentioned in the offer document of the Scheme, and the rules and regulations of the IFSCA, Prevention of Money Laundering Act, 2002, and any other applicable regulations, as amended from time to time, and agree to comply with and be bound by the same.</p>
              </td>
            </tr>
          </table>
          <table class="mb-2">
            <tr><th>Sole / First Applicant</th><th>Second Applicant</th><th>Third Applicant</th></tr>
            <tr>
              <td><div class="doc-sig-box">Awaiting e-signature</div></td>
              <td><div class="doc-sig-box">Not Applicable</div></td>
              <td><div class="doc-sig-box">Not Applicable</div></td>
            </tr>
          </table>
          <table>
            <tr>
              <td>Place: INDIA &nbsp;&nbsp;&nbsp; Date: ${renderBoxes(todayFormatted(), 8)}</td>
            </tr>
          </table>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">Instructions to Form</div>
          <ol class="text-[8.5px] text-slate-600 leading-relaxed" style="padding-left:14px; list-style:decimal;">
            <li class="mb-1">Please fill the form in BLOCK LETTERS in English.</li>
            <li class="mb-1">The name of investor including joint account holder should be as per PAN card details. CKYC – Cersai form is required if KIN not provided or there are changes in the KYC details. It must have Original seen &amp; verified ("OSV") stamp on all documents with Employee Name, Designation, Employee Code, Signature, Date &amp; stamp of Organization (SEBI/IFSCA registered intermediaries).</li>
            <li class="mb-1">In case of Joint investors, please provide the self-attested KYC documents for all Investors. Documents to be signed by the Guardian on behalf of Minor.</li>
            <li class="mb-1">Please provide correct Email ID and mobile number to ensure that critical updates are not missed.</li>
            <li class="mb-1">The address proof and communication set on the application form must be as per KYC. If your communication address is different from the registered address, proof of both addresses should be provided.</li>
            <li class="mb-1">Any specify mode of operations in case there is more than one Applicant. If not specified, all will be treated as Joint.</li>
            <li class="mb-1">In case the application is under Power of Attorney (PoA), a duly notarized copy of the PoA must be submitted along with the application form. All supporting documents must be signed by all holders including the PoA holder.</li>
            <li class="mb-1">Please make payments from your own accounts only; third-party payments are not accepted on the Bank Account from which funds are remitted.</li>
            <li class="mb-1">Residence for tax purposes — this field requires an indication of the country of residence for income tax purposes. If the individual is considered a resident for tax purposes of more than one country, then mention the final position after considering the tie breaker rules.</li>
            <li class="mb-1">"US Person" — the term United States person means: (a) an individual, citizen or resident of the United States of America; (b) a partnership or corporation organized in the laws of the United States of America or any State thereof; (c) a trust if a court within the United States would have authority under applicable law to render orders or judgements concerning substantially all issues regarding administration of the trust, and one or more US persons have authority to control all substantial decisions of the trust; (d) an estate of a decedent who is a citizen or resident of the United States of America.</li>
            <li class="mb-1">Applicants like Individuals (including sole proprietorship firm), joint applicants, are required to provide, in the applicable Application Form, details of country(ies) of Citizenship/Nationality mandatory. If the Place of Birth and Country of Citizenship/Nationality is other than India, then it is mandatory to provide the country of tax residence and relevant Taxpayer Identification Number to the Applicant(s)/Unit holders.</li>
            <li class="mb-1">If you have any questions about your tax residency or other definitions or terms, please contact your tax advisor. If you are a US citizen or resident or Green Card holder, please include United States in the foreign country information field along with any other country information, if applicable.</li>
            <li class="mb-1">It is mandatory to supply the Tax Identification Number (TIN) or functional equivalent like Social Security Number, National Insurance Number, Citizen/Company Identification Number or Resident Registration Number, if you do not have a TIN, then attach a copy of the documents mentioned in this section self-attested for status.</li>
            <li class="mb-1">Applicant/Unit holder should note that they also specifically authorize to disclose, share or remit in any form, mode or manner, all/any of the information provided by me/us, including all changes, updates to such information as and when provided to the FME, the Authorized Parties or any Indian or foreign governmental or statutory or judicial authorities/agencies including but not limited to the Financial Intelligence Unit-India (FIU-IND), the Authorised Dealer or other regulatory authorities/agencies without any obligation of advising me/us of the same.</li>
            <li class="mb-1">Please note that the specified information provided by the applicant/unit holder is found to be false or untrue or misrepresenting, applicant/unit holder will be solely liable and shall indemnify the FME, Trustees, their employees / associated persons / Service Providers.</li>
            <li>Scanned copies of the completed and duly signed form along with supporting documents to be e-mailed to <span class="text-blue-700">investoronboarding.gift@ppfas.com</span> and <span class="text-blue-700">gift_investoronboarding@mfapigift.in</span>. The Registrar &amp; Transfer Agent (RTA) will check the forms and confirm if the documents are in order. The physical application form along with documents should be courier'd to Computer Age Management Services Ltd (CAMS), Unit No. 409, BIFC Building, Zone-1, GIFT City, Gandhinagar, Gujarat – 382355. FATCA and CRS details are mandatory for all applicants/unit holders as per the Central Board of Direct Taxes (CBDT) notified Rules 114F to 114H under the Income Tax Rules, 1962.</li>
          </ol>
        </div>

        <div class="doc-page">
          <div class="doc-section-title">Uploaded Documents</div>
          <div class="doc-thumb-grid mb-1">${thumbHtml}</div>
        </div>

      </div>

      <div class="flex gap-2 mt-3">
        <button id="folioSignHereBtn" type="button" class="folio-sign-btn primary">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536M9 11l6.586-6.586a2 2 0 112.828 2.828L11.828 13.828 8 15l1.172-3.829z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M5 19h14"></path></svg>
          Sign
        </button>
        <button id="folioSignMailBtn" type="button" class="folio-sign-btn secondary">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
          Sign via Mail
        </button>
      </div>
    `;

    const downloadBtn = document.getElementById('folioDownloadPdfBtn');
    if (downloadBtn) downloadBtn.addEventListener('click', downloadReviewPdf);

    const signHereBtn = document.getElementById('folioSignHereBtn');
    const signMailBtn = document.getElementById('folioSignMailBtn');
    if (signHereBtn) signHereBtn.addEventListener('click', () => {
      fstate.signMethod = 'inapp';
      fstate.step = 4;
      render();
    });
    if (signMailBtn) signMailBtn.addEventListener('click', () => {
      fstate.signMethod = 'mail';
      fstate.step = 4;
      render();
    });
  }

  // --------------------------------------------------------------------------
  // PDF Export (client-side, via html2canvas + jsPDF)
  // --------------------------------------------------------------------------
  async function downloadReviewPdf() {
    const original = stepBody.querySelector('.folio-doc');
    const pageNodes = original ? Array.from(original.querySelectorAll('.doc-page')) : [];
    if (!original || !pageNodes.length) return;
    if (typeof window.html2canvas === 'undefined' || typeof window.jspdf === 'undefined') {
      alert('PDF export library failed to load. Check your connection and try again.');
      return;
    }

    const btn = document.getElementById('folioDownloadPdfBtn');
    const label = document.getElementById('folioDownloadPdfLabel');
    const prevLabel = label ? label.textContent : '';
    if (btn) btn.disabled = true;
    if (label) label.textContent = 'Preparing…';

    // Render each logical section (.doc-page) as its OWN PDF page, instead
    // of one long screenshot sliced by height. That old approach could cut
    // a table or paragraph in half wherever a page boundary happened to
    // fall; capturing per-page matches the real, printed form where the
    // cover, KYC/FATCA, bank/nomination, declarations, instructions, and
    // uploaded-documents sections are each on their own page.
    //
    // The container is `position:absolute` (not `fixed`) and anchored at
    // the real top of the document — html2canvas has a known bug where
    // `position:fixed` off-screen elements get shifted by the page's
    // current scroll offset during its internal document clone, which is
    // what caused the earlier "zoomed in and cut off" PDF.
    const container = document.createElement('div');
    container.style.position = 'absolute';
    container.style.left = '-9999px';
    container.style.top = '0px';
    container.style.width = `${original.offsetWidth}px`;
    container.style.background = '#ffffff';
    document.body.appendChild(container);

    const pageClones = pageNodes.map(node => {
      const clone = node.cloneNode(true);
      clone.classList.add('folio-doc', 'pdf-export-scale');
      clone.style.border = 'none';
      clone.style.borderBottom = 'none';
      clone.style.margin = '0';
      clone.style.padding = '20px';
      clone.style.width = `${original.offsetWidth}px`;
      clone.removeAttribute('id');
      container.appendChild(clone);
      return clone;
    });

    // Freshly cloned <img> tags (uploaded-document thumbnails) have to load
    // their blob: URL again even though the original element already had —
    // capturing before that finishes is what produced blank thumbnail boxes.
    const cloneImages = Array.from(container.querySelectorAll('img'));
    await Promise.all(cloneImages.map(img => {
      if (img.complete && img.naturalWidth > 0) return Promise.resolve();
      return new Promise(resolve => {
        img.addEventListener('load', resolve, { once: true });
        img.addEventListener('error', resolve, { once: true });
      });
    }));

    try {
      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF('p', 'pt', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeightPt = pdf.internal.pageSize.getHeight();

      for (let i = 0; i < pageClones.length; i++) {
        const clone = pageClones[i];
        // scale:1.5 (not 2) plus JPEG at 0.85 quality (not PNG) — seven
        // full-resolution PNG pages, several with photo thumbnails, produced
        // a 70MB+ PDF that's unusable as a download/e-mail attachment. This
        // combination keeps the form sharp and readable at a few MB instead.
        const canvas = await window.html2canvas(clone, {
          scale: 1.5,
          backgroundColor: '#ffffff',
          useCORS: true,
          scrollX: 0,
          scrollY: 0,
          windowWidth: clone.scrollWidth,
          windowHeight: clone.scrollHeight,
        });
        const imgData = canvas.toDataURL('image/jpeg', 0.85);
        let renderWidth = pageWidth;
        let renderHeight = (canvas.height * renderWidth) / canvas.width;
        // If a section is taller than one A4 page (e.g. a very long
        // declarations paragraph), scale it down to fit on a single page
        // rather than slicing it across two — every section keeps its own
        // page, same as the printed form.
        if (renderHeight > pageHeightPt) {
          const shrink = pageHeightPt / renderHeight;
          renderHeight = pageHeightPt;
          renderWidth = pageWidth * shrink;
        }
        const xOffset = (pageWidth - renderWidth) / 2;
        if (i > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', xOffset, 0, renderWidth, renderHeight, undefined, 'MEDIUM');
      }

      const c = getClient();
      const fileName = `GIFT_Outbound_Application_${c ? c.name.replace(/\s+/g, '_') : 'form'}.pdf`;
      pdf.save(fileName);
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('Could not generate the PDF. Please try again.');
    } finally {
      document.body.removeChild(container);
      if (btn) btn.disabled = false;
      if (label) label.textContent = prevLabel || 'Download PDF';
    }
  }

  function renderStepCompleted() {
    const c = getClient();
    const viaMail = fstate.signMethod !== 'inapp';
    const step1 = viaMail
      ? `${escapeHtml(c ? c.name : 'The investor')} needs to sign the filled form. They will receive it via email within the next ${fstate.signHours} hours.`
      : `${escapeHtml(c ? c.name : 'The investor')} has signed the filled form directly during this onboarding session.`;
    stepBody.innerHTML = `
      <div class="flex flex-col items-center justify-center text-center py-10">
        <div class="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>
        </div>
        <h3 class="text-lg font-black text-[var(--color-text)] mb-6">Form Completed</h3>
        <div class="w-full text-left bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-2xl p-4 space-y-3">
          <span class="text-[11px] font-extrabold uppercase tracking-widest text-blue-500">Next Steps</span>
          <div class="flex gap-2 text-xs text-[var(--color-text-muted)]">
            <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">1</span>
            <span>${step1}</span>
          </div>
          <div class="flex gap-2 text-xs text-[var(--color-text-muted)]">
            <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">2</span>
            <span>Once signed, the AMC will take 2–3 business days for folio creation.</span>
          </div>
          <div class="flex gap-2 text-xs text-[var(--color-text-muted)]">
            <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">3</span>
            <span>They can transact once the folio has been created.</span>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // Footer / Navigation
  // --------------------------------------------------------------------------
  function canProceed() {
    switch (fstate.step) {
      case 0: return fstate.clientId !== null;
      case 1: return fstate.documents.aadhaar && fstate.documents.pan && fstate.documents.bank;
      case 2: {
        if (fstate.ckyc.length !== 14 || !fstate.occupation) return false;
        if (EMPLOYER_OCCUPATIONS.includes(fstate.occupation) && (!fstate.employerName.trim() || !fstate.placeOfWork.trim())) return false;
        if (BUSINESS_OCCUPATIONS.includes(fstate.occupation) && (!fstate.businessName.trim() || !fstate.businessNature.trim())) return false;
        return true;
      }
      case 3: return true;
      default: return true;
    }
  }

  function updateFooter() {
    if (fstate.step === 4) {
      footerNav.classList.add('justify-center');
      backBtn.classList.add('hidden');
      nextBtn.classList.remove('hidden');
      nextLabel.textContent = 'Done';
      nextBtn.disabled = false;
      nextBtn.classList.remove('opacity-40', 'cursor-not-allowed');
      return;
    }
    if (fstate.step === 3) {
      // Review step has its own Sign / Sign via Mail buttons inside the
      // card, so the shared footer only needs Back.
      footerNav.classList.remove('justify-center');
      backBtn.classList.remove('hidden');
      nextBtn.classList.add('hidden');
      return;
    }
    footerNav.classList.remove('justify-center');
    backBtn.classList.toggle('hidden', fstate.step === 0);
    nextBtn.classList.remove('hidden');
    nextLabel.textContent = fstate.step === 2 ? 'Submit' : 'Continue';
    const ok = canProceed();
    nextBtn.disabled = !ok;
    nextBtn.classList.toggle('opacity-40', !ok);
    nextBtn.classList.toggle('cursor-not-allowed', !ok);
  }

  function render() {
    updateProgress();
    updateSidePanel();

    const progressWrap = document.querySelector('.folio-progress-track');
    progressWrap.style.display = fstate.step === 4 ? 'none' : 'flex';

    switch (fstate.step) {
      case 0: renderStepClient(); break;
      case 1: renderStepDocuments(); break;
      case 2: renderStepCkyc(); break;
      case 3: renderStepReview(); break;
      case 4: renderStepCompleted(); break;
    }
    updateFooter();
  }

  backBtn.addEventListener('click', () => {
    if (fstate.step > 0) {
      fstate.step -= 1;
      render();
    }
  });

  nextBtn.addEventListener('click', () => {
    if (nextBtn.disabled) return;
    if (fstate.step === 4) {
      closeModal();
      return;
    }
    fstate.step += 1;
    render();
  });

  document.getElementById('folioCloseBtn').addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  const navBtn = document.getElementById('navOnboardBtn');
  const promoBtn = document.getElementById('promoOnboardBtn');
  if (navBtn) navBtn.addEventListener('click', openModal);
  if (promoBtn) promoBtn.addEventListener('click', openModal);
});
