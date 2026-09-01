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

  const SIDE_PANELS = [
    {
      theme: '',
      title: 'Invest in Global Assets <span class="text-blue-400">without the offshore complexity.</span>',
      subtitle: 'Access US equities, global ETFs, and international funds from a single GIFT City account.',
    },
    {
      theme: 'side-warm',
      title: 'Overcome <span class="text-amber-300">Domestic Investment Limits.</span>',
      subtitle: 'GIFT City lets qualified investors allocate up to $250,000 every year, legally and seamlessly.',
    },
    {
      theme: 'side-purple',
      title: 'International Diversification, <span class="text-indigo-300">always stay on top.</span>',
      subtitle: 'Global benchmarks have historically outpaced domestic ones over the long run — diversify beyond borders.',
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
  };

  const modal = document.getElementById('folioModal');
  const sidePanel = document.getElementById('folioSidePanel');
  const sideTitle = document.getElementById('folioSideTitle');
  const sideSubtitle = document.getElementById('folioSideSubtitle');
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
                <span class="truncate">${fstate.documents[r.key] ? escapeHtml(fstate.documents[r.key]) : 'Upload file — jpg, png, or pdf (max 5mb)'}</span>
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
          fstate.documents[key] = file.name;
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

    stepBody.innerHTML = `
      <h3 class="text-lg font-black text-[var(--color-text)] mb-1">Review</h3>
      <p class="text-xs text-[var(--color-text-muted)] mb-3">Confirm the generated application form before sending it for e-signature.</p>
      <div class="folio-doc p-3 max-h-[420px] overflow-y-auto">

        <div class="text-center border-2 border-slate-400 rounded-lg p-2 mb-2">
          <div class="font-black text-[11px]">GIFT360 CAPITAL ADVISORS PRIVATE LIMITED</div>
          <div class="font-bold text-[10px]">Application Form for Outbound Funds (Individual)</div>
          <div class="text-[9px] text-slate-500">Scheme Applied For: ${escapeHtml(SCHEME_NAME)}</div>
        </div>

        <table class="mb-2">
          <tr>
            <th style="width:25%">Distributor</th><th style="width:25%">Code</th><th style="width:30%">Email</th><th style="width:20%">Mobile</th>
          </tr>
          <tr>
            <td>GIFT360 Capital Advisors</td><td>GC100450</td><td>onboarding@gift360.in</td><td>9999900000</td>
          </tr>
        </table>

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
            <span class="doc-check checked">✓</span> Single &nbsp;&nbsp; <span class="doc-check">✓</span> Joint &nbsp;&nbsp; <span class="doc-check">✓</span> Minor &nbsp; <span class="text-slate-400 text-[9px]">(Mode of Operation)</span>
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

        <div class="doc-section-title">II &nbsp; KYC Details</div>
        <table class="mb-2">
          <tr>
            <td style="width:55%">
              <span class="doc-field-label">Occupation</span>
              <div class="grid grid-cols-2 gap-x-2 gap-y-0.5 mt-1">${occChecks}</div>
            </td>
            <td>
              <span class="doc-field-label">Gross Annual Income</span>
              <div class="grid grid-cols-1 gap-y-0.5 mt-1">${incomeChecks}</div>
            </td>
          </tr>
          <tr><td colspan="2">
            <span class="doc-field-label">PEP Disclosure</span>
            <span class="doc-check checked">✓</span> Not a Politically Exposed Person
          </td></tr>
          ${showEmployer ? `
          <tr>
            <td><span class="doc-field-label">Name of Employer</span>${escapeHtml(fstate.employerName) || '—'}</td>
            <td><span class="doc-field-label">Place of Work</span>${escapeHtml(fstate.placeOfWork) || '—'}</td>
          </tr>` : ''}
          ${showBusiness ? `
          <tr>
            <td><span class="doc-field-label">Name of Business</span>${escapeHtml(fstate.businessName) || '—'}</td>
            <td><span class="doc-field-label">Nature of Business</span>${escapeHtml(fstate.businessNature) || '—'}</td>
          </tr>` : ''}
        </table>

        <div class="doc-section-title">III &nbsp; FATCA &amp; CRS Details</div>
        <table class="mb-2">
          <tr>
            <td><span class="doc-check checked">✓</span> Country of Birth: India</td>
            <td><span class="doc-check checked">✓</span> Citizenship / Nationality: Indian</td>
            <td><span class="doc-check checked">✓</span> US Person: No</td>
          </tr>
        </table>

        <div class="doc-section-title">IV &nbsp; Bank Account Details</div>
        <table class="mb-2">
          <tr>
            <td><span class="doc-field-label">Account Number</span>${renderBoxes(c.bank.account, 16)}</td>
          </tr>
          <tr>
            <td><span class="doc-check checked">✓</span> Savings</td>
            <td><span class="doc-field-label">Name of Bank / Branch</span>${escapeHtml(c.bank.bankName)}, ${escapeHtml(c.bank.branch)}</td>
            <td><span class="doc-field-label">IFSC Code</span>${escapeHtml(c.bank.ifsc)}</td>
          </tr>
        </table>

        <div class="doc-section-title">V &nbsp; Nomination Details</div>
        <table class="mb-2">
          <tr><th>Nominee Name</th><th>Date of Birth</th><th>Relationship</th><th>Mobile</th><th>Share</th></tr>
          <tr>
            <td>${escapeHtml(c.nominee.name)}</td><td>${escapeHtml(c.nominee.dob)}</td>
            <td>${escapeHtml(c.nominee.relation)}</td><td>${escapeHtml(c.nominee.mobile)}</td><td>100%</td>
          </tr>
        </table>

        <div class="doc-section-title">VI &nbsp; Declarations &amp; Signature</div>
        <table>
          <tr>
            <td class="text-[9px] text-slate-600">I/We hereby declare that all the information and particulars given by me/us in this application form are true, complete and accurate, and agree to the terms and conditions governing GIFT City IFSC outbound investments.</td>
          </tr>
          <tr>
            <td>
              <div class="doc-sig-box">Awaiting e-signature</div>
            </td>
          </tr>
          <tr>
            <td>Place: INDIA &nbsp;&nbsp;&nbsp; Date: ${renderBoxes(todayFormatted(), 8)}</td>
          </tr>
        </table>

      </div>
    `;
  }

  function renderStepCompleted() {
    const c = getClient();
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
            <span>${escapeHtml(c ? c.name : 'The investor')} needs to sign the filled form. They will receive it via email within the next ${fstate.signHours} hours.</span>
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
      nextLabel.textContent = 'Done';
      nextBtn.disabled = false;
      nextBtn.classList.remove('opacity-40', 'cursor-not-allowed');
      return;
    }
    footerNav.classList.remove('justify-center');
    backBtn.classList.toggle('hidden', fstate.step === 0);
    nextLabel.textContent = fstate.step === 2 ? 'Submit' : (fstate.step === 3 ? 'Continue' : 'Continue');
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
