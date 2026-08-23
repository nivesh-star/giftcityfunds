/**
 * fund_detail.js
 * Controller for the standalone /fund/<id> page. This is the same fund
 * detail content that used to live inside a modal overlay on the dashboard
 * (see app.js's old openFundDetail) -- now rendered as its own full page,
 * fetched via the same /api/fund/<id> and /api/fund/<id>/nav-history
 * endpoints, so it stays a single source of truth for fund data.
 */

document.addEventListener('DOMContentLoaded', () => {
  const state = {
    currentModalFund: null,
    currentBuyQuote: null,
    charts: {},
  };

  // --------------------------------------------------------------------------
  // Theme Management
  // --------------------------------------------------------------------------
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const storedTheme = localStorage.getItem('gift360-theme') || 'dark';

  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    }
    localStorage.setItem('gift360-theme', theme);
  }

  applyTheme(storedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const isLight = document.documentElement.classList.contains('light');
      applyTheme(isLight ? 'dark' : 'light');
      if (state.currentModalFund && state.fullNavHistory) updateNavChart(state.navRange || 'ALL');
    });
  }

  // --------------------------------------------------------------------------
  // Utility
  // --------------------------------------------------------------------------
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function fmtUsd(n) { return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function fmtInr(n) { return '₹' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  // --------------------------------------------------------------------------
  // Geographic Allocation Map
  // --------------------------------------------------------------------------
  // Maps common country names (as they appear in factsheet-sourced allocation
  // data) to ISO 3166-1 alpha-2 codes, which is what jsVectorMap's bundled
  // 'world' map keys its regions by. Generic/regional buckets (Europe, Asia,
  // Cash & Equivalents, etc.) intentionally have no entry here -- they stay
  // in the text list below the map but are never guessed at on the map
  // itself, since there's no single real country to highlight for them.
  const COUNTRY_NAME_TO_ISO2 = {
    'united states': 'US', 'usa': 'US', 'us': 'US',
    'india': 'IN', 'china': 'CN', 'hong kong': 'HK', 'taiwan': 'TW',
    'japan': 'JP', 'south korea': 'KR', 'korea': 'KR',
    'united kingdom': 'GB', 'uk': 'GB', 'germany': 'DE', 'france': 'FR',
    'switzerland': 'CH', 'netherlands': 'NL', 'ireland': 'IE',
    'canada': 'CA', 'australia': 'AU', 'singapore': 'SG', 'brazil': 'BR',
    'italy': 'IT', 'spain': 'ES', 'sweden': 'SE', 'denmark': 'DK',
    'norway': 'NO', 'finland': 'FI', 'israel': 'IL', 'mexico': 'MX',
    'indonesia': 'ID', 'south africa': 'ZA', 'russia': 'RU',
    'saudi arabia': 'SA', 'united arab emirates': 'AE', 'uae': 'AE',
    'vietnam': 'VN', 'thailand': 'TH', 'malaysia': 'MY',
    'philippines': 'PH', 'poland': 'PL', 'turkey': 'TR',
    'new zealand': 'NZ', 'belgium': 'BE', 'austria': 'AT',
    'portugal': 'PT', 'luxembourg': 'LU', 'egypt': 'EG', 'chile': 'CL',
    'argentina': 'AR', 'colombia': 'CO', 'peru': 'PE', 'qatar': 'QA',
    'kuwait': 'KW',
  };

  // A category like "China + Taiwan + Hong Kong" or "US & Canada" bundles
  // several countries' weight into one disclosed figure -- split it and
  // credit each recognized country the full bundled weight (best-effort;
  // factsheets don't disclose the per-country split within the bundle).
  function countriesInCategory(category) {
    return String(category || '')
      .split(/[+&/]| and /i)
      .map(part => COUNTRY_NAME_TO_ISO2[part.trim().toLowerCase()])
      .filter(Boolean);
  }

  function renderGeoMap(geoItems) {
    const wrapper = document.getElementById('modalGeoMapWrapper');
    const mapEl = document.getElementById('modalGeoMap');
    if (!wrapper || !mapEl) return;

    const values = {};
    geoItems.forEach(item => {
      const codes = countriesInCategory(item.category);
      codes.forEach(code => {
        values[code] = (values[code] || 0) + (item.weight_pct || 0);
      });
    });

    const codes = Object.keys(values);
    if (codes.length === 0 || typeof jsVectorMap === 'undefined') {
      wrapper.classList.add('hidden');
      return;
    }

    wrapper.classList.remove('hidden');
    mapEl.innerHTML = '';

    const isLight = document.documentElement.classList.contains('light');
    try {
      new jsVectorMap({
        selector: '#modalGeoMap',
        map: 'world',
        zoomButtons: false,
        zoomOnScroll: false,
        backgroundColor: 'transparent',
        regionStyle: {
          initial: { fill: isLight ? '#e2e8f0' : '#1e293b', stroke: isLight ? '#cbd5e1' : '#334155', strokeWidth: 0.5 },
          hover: { fill: '#2563eb' },
        },
        series: {
          regions: [{
            values,
            scale: ['#93c5fd', '#1d4ed8'],
            normalizeFunction: 'polynomial',
          }],
        },
        onRegionTooltipShow(event, tooltip, code) {
          if (values[code] != null) {
            tooltip.text(`${tooltip.text()}: ${values[code].toFixed(1)}%`);
          }
        },
      });
    } catch (e) {
      console.error('Error rendering geographic map:', e);
      wrapper.classList.add('hidden');
    }
  }

  function renderAllocationBars(items) {
    const sorted = [...items].sort((a, b) => (b.weight_pct || 0) - (a.weight_pct || 0));
    const maxWeight = Math.max(...sorted.map(i => i.weight_pct || 0), 1);
    return sorted.map(i => `
      <div class="flex items-center gap-2">
        <span class="text-[11px] text-[var(--color-text-muted)] w-1/3 truncate">${escapeHtml(i.category)}</span>
        <div class="flex-1 h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
          <div class="h-full bg-emerald-400 rounded-full" style="width:${((i.weight_pct || 0) / maxWeight * 100).toFixed(1)}%"></div>
        </div>
        <span class="text-[11px] font-mono text-[var(--color-text)] w-12 text-right">${i.weight_pct != null ? i.weight_pct.toFixed(1) + '%' : '—'}</span>
      </div>
    `).join('');
  }

  // --------------------------------------------------------------------------
  // Buy Panel
  // --------------------------------------------------------------------------
  function setupBuyPanel(f) {
    const loggedOutEl = document.getElementById('modalBuyLoggedOut');
    const noNavEl = document.getElementById('modalBuyNoNav');
    const formEl = document.getElementById('modalBuyForm');
    const summaryEl = document.getElementById('modalBuySummary');
    const successEl = document.getElementById('modalBuySuccess');
    const errorEl = document.getElementById('modalBuyError');
    if (!loggedOutEl || !formEl) return;

    [loggedOutEl, noNavEl, formEl, summaryEl, successEl].forEach(el => el.classList.add('hidden'));
    if (errorEl) { errorEl.classList.add('hidden'); errorEl.textContent = ''; }
    const amountInput = document.getElementById('modalBuyAmount');
    if (amountInput) amountInput.value = '';

    if (!window.GIFT360_LOGGED_IN) {
      loggedOutEl.classList.remove('hidden');
    } else if (f.nav === null || f.nav === undefined) {
      noNavEl.classList.remove('hidden');
    } else {
      formEl.classList.remove('hidden');
    }
  }

  async function requestBuyQuote() {
    const fund = state.currentModalFund;
    if (!fund) return;
    const amountInput = document.getElementById('modalBuyAmount');
    const errorEl = document.getElementById('modalBuyError');
    const amount = parseFloat(amountInput ? amountInput.value : '');

    if (!amount || amount < 500) {
      if (errorEl) { errorEl.textContent = 'Minimum investment is $500.'; errorEl.classList.remove('hidden'); }
      return;
    }
    if (errorEl) errorEl.classList.add('hidden');

    const btn = document.getElementById('modalBuyProceedBtn');
    const originalText = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Loading…'; }

    try {
      const res = await fetch('/api/buy/quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fund_id: fund.id, amount: amount }),
      });
      const data = await res.json();
      if (!data.success) {
        if (errorEl) { errorEl.textContent = data.error || 'Could not fetch quote.'; errorEl.classList.remove('hidden'); }
        return;
      }

      const q = data.quote;
      state.currentBuyQuote = q;
      document.getElementById('sumAmount').textContent = fmtUsd(q.amount);
      document.getElementById('sumFee').textContent = fmtUsd(q.transaction_fee);
      document.getElementById('sumSubtotal').textContent = fmtUsd(q.subtotal_usd);
      document.getElementById('sumFx').textContent = `~${q.fx_rate} → ${fmtInr(q.subtotal_inr)}`;
      document.getElementById('sumGst').textContent = fmtInr(q.gst_inr);
      document.getElementById('sumPayable').textContent = fmtInr(q.payable_inr);
      document.getElementById('sumBank').textContent = `From: ${q.linked_bank} · Folio ${q.folio}`;

      document.getElementById('modalBuyForm').classList.add('hidden');
      document.getElementById('modalBuySummary').classList.remove('hidden');
    } catch (e) {
      if (errorEl) { errorEl.textContent = 'Network error — please try again.'; errorEl.classList.remove('hidden'); }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = originalText; }
    }
  }

  async function submitBuyOrder() {
    const fund = state.currentModalFund;
    const quote = state.currentBuyQuote;
    if (!fund || !quote) return;

    const btn = document.getElementById('modalBuyNotifyBtn');
    const originalText = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }

    try {
      const res = await fetch('/api/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fund_id: fund.id, amount: quote.amount }),
      });
      const data = await res.json();

      if (!data.success) {
        document.getElementById('modalBuySummary').classList.add('hidden');
        document.getElementById('modalBuyForm').classList.remove('hidden');
        const errorEl = document.getElementById('modalBuyError');
        if (errorEl) { errorEl.textContent = data.error || 'Purchase failed. Please try again.'; errorEl.classList.remove('hidden'); }
        return;
      }

      document.getElementById('modalBuySummary').classList.add('hidden');
      const successEl = document.getElementById('modalBuySuccess');
      const detailEl = document.getElementById('modalBuySuccessDetail');
      if (detailEl) {
        detailEl.textContent = `${data.order.units} units of ${data.order.fund_name} allotted at NAV ${data.order.nav} ${data.order.currency} · Folio ${data.order.folio}`;
      }
      successEl.classList.remove('hidden');
    } catch (e) {
      // Network failure -- leave the summary visible so the presenter can retry
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = originalText; }
    }
  }

  function backToBuyForm() {
    document.getElementById('modalBuySummary').classList.add('hidden');
    document.getElementById('modalBuyForm').classList.remove('hidden');
  }

  const modalBuyProceedBtnEl = document.getElementById('modalBuyProceedBtn');
  if (modalBuyProceedBtnEl) modalBuyProceedBtnEl.addEventListener('click', requestBuyQuote);

  const modalBuyNotifyBtnEl = document.getElementById('modalBuyNotifyBtn');
  if (modalBuyNotifyBtnEl) modalBuyNotifyBtnEl.addEventListener('click', submitBuyOrder);

  const modalBuyBackBtnEl = document.getElementById('modalBuyBackBtn');
  if (modalBuyBackBtnEl) modalBuyBackBtnEl.addEventListener('click', backToBuyForm);

  // --------------------------------------------------------------------------
  // Data sections (holdings, allocation, taxation, share classes, etc.)
  // --------------------------------------------------------------------------
  function renderDataSections(f) {
    const feeNotesSection = document.getElementById('modalFeeNotesSection');
    const feeNotesBody = document.getElementById('modalFeeNotesBody');
    const underlyingSection = document.getElementById('modalUnderlyingSection');
    const underlyingBody = document.getElementById('modalUnderlyingBody');
    const holdingsSection = document.getElementById('modalHoldingsSection');
    const holdingsBody = document.getElementById('modalHoldingsBody');
    const holdingsBasisNote = document.getElementById('modalHoldingsBasisNote');
    const geoSection = document.getElementById('modalGeoSection');
    const geoBody = document.getElementById('modalGeoBody');
    const sectorSection = document.getElementById('modalSectorSection');
    const sectorBody = document.getElementById('modalSectorBody');
    const marketCapSection = document.getElementById('modalMarketCapSection');
    const marketCapBody = document.getElementById('modalMarketCapBody');
    const assetClassSection = document.getElementById('modalAssetClassSection');
    const assetClassBody = document.getElementById('modalAssetClassBody');
    const taxSection = document.getElementById('modalTaxSection');
    const taxBody = document.getElementById('modalTaxBody');
    const shareClassSection = document.getElementById('modalShareClassSection');
    const shareClassBody = document.getElementById('modalShareClassBody');
    const performanceSection = document.getElementById('modalPerformanceSection');
    const performanceBody = document.getElementById('modalPerformanceBody');
    const riskMetricsSection = document.getElementById('modalRiskMetricsSection');
    const riskMetricsBody = document.getElementById('modalRiskMetricsBody');
    const pendingSection = document.getElementById('modalDataPendingSection');

    let anyRendered = false;

    if (feeNotesSection && feeNotesBody) {
      if (f.fee_notes) {
        anyRendered = true;
        feeNotesBody.textContent = f.fee_notes;
        feeNotesSection.classList.remove('hidden');
      } else {
        feeNotesSection.classList.add('hidden');
      }
    }

    if (underlyingSection && underlyingBody) {
      if (f.underlying_fund_name) {
        anyRendered = true;
        underlyingBody.innerHTML = `
          <div><span class="text-[var(--color-text-subtle)]">Fund:</span> <span class="font-semibold text-[var(--color-text)]">${escapeHtml(f.underlying_fund_name)}</span></div>
          ${f.underlying_fund_manager ? `<div><span class="text-[var(--color-text-subtle)]">Manager:</span> ${escapeHtml(f.underlying_fund_manager)}</div>` : ''}
          ${f.underlying_fund_domicile ? `<div><span class="text-[var(--color-text-subtle)]">Domicile:</span> ${escapeHtml(f.underlying_fund_domicile)}</div>` : ''}
        `;
        underlyingSection.classList.remove('hidden');
      } else {
        underlyingSection.classList.add('hidden');
      }
    }

    if (holdingsSection && holdingsBody) {
      const holdings = Array.isArray(f.holdings) ? f.holdings : [];
      if (holdings.length > 0) {
        anyRendered = true;
        if (holdingsBasisNote) holdingsBasisNote.textContent = '';
        const directHoldings = holdings.filter(h => h.holdings_basis !== 'underlying_fund');
        const underlyingHoldings = holdings.filter(h => h.holdings_basis === 'underlying_fund');
        const groups = [];
        if (directHoldings.length) groups.push({ label: 'Direct Holdings', rows: directHoldings, id: 'direct' });
        if (underlyingHoldings.length) groups.push({ label: 'Look-through: Underlying Fund Holdings', rows: underlyingHoldings, id: 'underlying' });

        const INITIAL_SHOW = 10;
        holdingsBody.innerHTML = groups.map(g => {
          const maxWeight = Math.max(...g.rows.map(h => h.weight_pct || 0), 1);
          const rowHtml = (h) => `
            <div class="flex items-center gap-2 mb-1.5 last:mb-0">
              <span class="text-[11px] text-[var(--color-text-muted)] w-1/2 truncate">${escapeHtml(h.holding_name)}</span>
              <div class="flex-1 h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div class="h-full bg-blue-400 rounded-full" style="width:${((h.weight_pct || 0) / maxWeight * 100).toFixed(1)}%"></div>
              </div>
              <span class="text-[11px] font-mono text-[var(--color-text)] w-12 text-right">${h.weight_pct != null ? h.weight_pct.toFixed(1) + '%' : '—'}</span>
            </div>
          `;
          const visibleRows = g.rows.slice(0, INITIAL_SHOW).map(rowHtml).join('');
          const hiddenRows = g.rows.slice(INITIAL_SHOW).map(rowHtml).join('');
          const groupHeader = groups.length > 1
            ? `<div class="text-[10px] font-semibold text-[var(--color-text-subtle)] uppercase tracking-wide mb-1.5 ${g.id === 'underlying' ? 'mt-3' : ''}">${escapeHtml(g.label)}</div>`
            : '';
          const toggleId = `holdings-more-${g.id}`;
          const toggleBtn = hiddenRows
            ? `<button type="button" onclick="
                 const box = document.getElementById('${toggleId}');
                 const expanded = box.classList.toggle('hidden');
                 this.textContent = expanded ? 'Show all ${g.rows.length} holdings' : 'Show less';
               " class="text-[10px] text-blue-400 hover:underline mt-1">Show all ${g.rows.length} holdings</button>`
            : '';
          return `
            <div class="mb-2 last:mb-0">
              ${groupHeader}
              ${visibleRows}
              <div id="${toggleId}" class="hidden">${hiddenRows}</div>
              ${toggleBtn}
            </div>
          `;
        }).join('');
        holdingsSection.classList.remove('hidden');
      } else {
        holdingsSection.classList.add('hidden');
      }
    }

    if (geoSection && geoBody) {
      const geo = Array.isArray(f.geographic_allocation) ? f.geographic_allocation : [];
      if (geo.length > 0) {
        anyRendered = true;
        geoBody.innerHTML = renderAllocationBars(geo);
        geoSection.classList.remove('hidden');
        renderGeoMap(geo);
      } else {
        geoSection.classList.add('hidden');
        const mapWrapper = document.getElementById('modalGeoMapWrapper');
        if (mapWrapper) mapWrapper.classList.add('hidden');
      }
    }

    if (sectorSection && sectorBody) {
      const sector = Array.isArray(f.sector_allocation) ? f.sector_allocation : [];
      if (sector.length > 0) { anyRendered = true; sectorBody.innerHTML = renderAllocationBars(sector); sectorSection.classList.remove('hidden'); }
      else sectorSection.classList.add('hidden');
    }

    if (marketCapSection && marketCapBody) {
      const mcap = Array.isArray(f.market_cap_allocation) ? f.market_cap_allocation : [];
      if (mcap.length > 0) { anyRendered = true; marketCapBody.innerHTML = renderAllocationBars(mcap); marketCapSection.classList.remove('hidden'); }
      else marketCapSection.classList.add('hidden');
    }

    if (assetClassSection && assetClassBody) {
      const assetClass = Array.isArray(f.asset_class_allocation) ? f.asset_class_allocation : [];
      if (assetClass.length > 0) { anyRendered = true; assetClassBody.innerHTML = renderAllocationBars(assetClass); assetClassSection.classList.remove('hidden'); }
      else assetClassSection.classList.add('hidden');
    }

    if (taxSection && taxBody) {
      const tax = f.taxation;
      if (tax && (tax.ltcg_rate || tax.stcg_rate || tax.dividend_rate || tax.tax_notes)) {
        anyRendered = true;
        const rateRows = [];
        if (tax.ltcg_rate) rateRows.push(`<div><span class="text-[var(--color-text-subtle)]">LTCG:</span> <span class="font-mono font-semibold text-[var(--color-text)]">${escapeHtml(tax.ltcg_rate)}</span></div>`);
        if (tax.stcg_rate) rateRows.push(`<div><span class="text-[var(--color-text-subtle)]">STCG:</span> <span class="font-mono font-semibold text-[var(--color-text)]">${escapeHtml(tax.stcg_rate)}</span></div>`);
        if (tax.dividend_rate) rateRows.push(`<div><span class="text-[var(--color-text-subtle)]">Dividend:</span> <span class="font-mono font-semibold text-[var(--color-text)]">${escapeHtml(tax.dividend_rate)}</span></div>`);
        taxBody.innerHTML = `
          ${rateRows.length ? `<div class="grid grid-cols-3 gap-2 mb-2">${rateRows.join('')}</div>` : ''}
          ${tax.tax_notes ? `<div class="text-[var(--color-text-subtle)] italic">${escapeHtml(tax.tax_notes)}</div>` : ''}
        `;
        taxSection.classList.remove('hidden');
      } else {
        taxSection.classList.add('hidden');
      }
    }

    if (shareClassSection && shareClassBody) {
      const classes = Array.isArray(f.share_classes) ? f.share_classes : [];
      if (classes.length > 0) {
        anyRendered = true;
        shareClassBody.innerHTML = `
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="text-[10px] text-[var(--color-text-subtle)] uppercase tracking-wide">
                <th class="pb-1.5 pr-3">Class</th>
                <th class="pb-1.5 pr-3">NAV</th>
                <th class="pb-1.5 pr-3">Mgmt Fee</th>
                <th class="pb-1.5 pr-3">TER</th>
                <th class="pb-1.5 pr-3">Min. Investment</th>
                <th class="pb-1.5">Exit Load</th>
              </tr>
            </thead>
            <tbody>
              ${classes.map(c => {
                let navCell;
                if (c.subscription_nav != null || c.redemption_nav_long_term != null || c.redemption_nav_short_term != null) {
                  navCell = `
                    <div class="leading-tight">
                      <div>Sub: ${c.subscription_nav != null ? c.subscription_nav : '—'}</div>
                      <div>Redeem (LT): ${c.redemption_nav_long_term != null ? c.redemption_nav_long_term : '—'}</div>
                      <div>Redeem (ST): ${c.redemption_nav_short_term != null ? c.redemption_nav_short_term : '—'}</div>
                    </div>
                  `;
                } else {
                  navCell = c.nav != null ? c.nav : '—';
                }
                return `
                <tr class="border-t border-[var(--color-border)]">
                  <td class="py-1.5 pr-3 font-semibold text-[var(--color-text)]">${escapeHtml(c.class_name || '—')}</td>
                  <td class="py-1.5 pr-3 font-mono">${navCell}</td>
                  <td class="py-1.5 pr-3 font-mono">${c.management_fee_pct != null ? c.management_fee_pct + '%' : '—'}</td>
                  <td class="py-1.5 pr-3 font-mono">${c.ter_pct != null ? c.ter_pct + '%' : '—'}</td>
                  <td class="py-1.5 pr-3 font-mono">${c.min_investment_usd != null ? '$' + c.min_investment_usd.toLocaleString() : '—'}</td>
                  <td class="py-1.5 font-mono">${c.exit_load_pct != null ? c.exit_load_pct + '%' + (c.exit_load_months ? ' (' + c.exit_load_months + 'mo)' : '') : '—'}</td>
                </tr>
              `;
              }).join('')}
            </tbody>
          </table>
        `;
        shareClassSection.classList.remove('hidden');
      } else {
        shareClassSection.classList.add('hidden');
      }
    }

    if (performanceSection && performanceBody) {
      const perf = Array.isArray(f.performance) ? f.performance : [];
      if (perf.length > 0) {
        anyRendered = true;
        performanceBody.innerHTML = `
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="text-[10px] text-[var(--color-text-subtle)] uppercase tracking-wide">
                <th class="pb-1.5 pr-3">Period</th>
                <th class="pb-1.5 pr-3">Class</th>
                <th class="pb-1.5 pr-3">Fund</th>
                <th class="pb-1.5 pr-3">Benchmark</th>
                <th class="pb-1.5">Excess</th>
              </tr>
            </thead>
            <tbody>
              ${perf.map(p => `
                <tr class="border-t border-[var(--color-border)]">
                  <td class="py-1.5 pr-3 font-semibold text-[var(--color-text)]">${escapeHtml(p.period || '—')}</td>
                  <td class="py-1.5 pr-3">${escapeHtml(p.share_class || '—')}</td>
                  <td class="py-1.5 pr-3 font-mono">${p.fund_return_pct != null ? p.fund_return_pct + '%' : '—'}</td>
                  <td class="py-1.5 pr-3 font-mono">${p.benchmark_return_pct != null ? p.benchmark_return_pct + '%' : '—'}</td>
                  <td class="py-1.5 font-mono ${p.excess_return_pct > 0 ? 'text-emerald-400' : p.excess_return_pct < 0 ? 'text-red-400' : ''}">${p.excess_return_pct != null ? p.excess_return_pct + '%' : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
        performanceSection.classList.remove('hidden');
      } else {
        performanceSection.classList.add('hidden');
      }
    }

    if (riskMetricsSection && riskMetricsBody) {
      const risk = Array.isArray(f.risk_metrics) ? f.risk_metrics : [];
      const metricLabels = {
        alpha_pct: 'Alpha', beta: 'Beta', r_squared: 'R²',
        tracking_error_pct: 'Tracking Error', information_ratio: 'Info. Ratio',
        sharpe_ratio: 'Sharpe', upside_capture_pct: 'Upside Capture',
        downside_capture_pct: 'Downside Capture', active_share_pct: 'Active Share',
        batting_average_pct: 'Batting Avg.',
      };
      const tiles = [];
      risk.forEach(rm => {
        Object.keys(metricLabels).forEach(key => {
          if (rm[key] != null) {
            const isPct = key.endsWith('_pct');
            tiles.push(`
              <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl px-2.5 py-2">
                <div class="text-[9px] text-[var(--color-text-subtle)] uppercase tracking-wide">${metricLabels[key]}${rm.period ? ' (' + escapeHtml(rm.period) + ')' : ''}</div>
                <div class="text-sm font-mono font-semibold text-[var(--color-text)]">${rm[key]}${isPct ? '%' : ''}</div>
              </div>
            `);
          }
        });
      });
      if (tiles.length > 0) { anyRendered = true; riskMetricsBody.innerHTML = tiles.join(''); riskMetricsSection.classList.remove('hidden'); }
      else riskMetricsSection.classList.add('hidden');
    }

    if (pendingSection) pendingSection.classList.toggle('hidden', anyRendered);
  }

  // --------------------------------------------------------------------------
  // NAV Chart
  // --------------------------------------------------------------------------
  const NAV_RANGES = ['YTD', '1M', '3M', '1Y', '3Y', '5Y', 'ALL'];

  // Filters the fund's full recorded NAV history down to a time-range tab.
  // With sparse real data (most funds have 1-2 recorded points so far),
  // a narrow range can legitimately contain zero points -- that's shown
  // honestly rather than stretched to fill the window.
  function filterHistoryByRange(fullHistory, range) {
    if (!fullHistory || fullHistory.length === 0 || range === 'ALL') return fullHistory || [];
    const now = new Date();
    let cutoff;
    if (range === 'YTD') {
      cutoff = new Date(now.getFullYear(), 0, 1);
    } else {
      const monthsBack = { '1M': 1, '3M': 3, '1Y': 12, '3Y': 36, '5Y': 60 }[range] || 0;
      cutoff = new Date(now);
      cutoff.setMonth(cutoff.getMonth() - monthsBack);
    }
    return fullHistory.filter(h => {
      const d = new Date(h.nav_date);
      return !isNaN(d) && d >= cutoff;
    });
  }

  function setActiveRangeTab(range) {
    document.querySelectorAll('.nav-range-tab').forEach(btn => {
      const isActive = btn.getAttribute('data-range') === range;
      btn.classList.toggle('bg-blue-600', isActive);
      btn.classList.toggle('text-white', isActive);
      btn.classList.toggle('text-[var(--color-text-muted)]', !isActive);
    });
  }

  function updateNavChart(range) {
    state.navRange = range;
    setActiveRangeTab(range);
    const filtered = filterHistoryByRange(state.fullNavHistory, range);
    const emptyMessage = (state.fullNavHistory && state.fullNavHistory.length > 0 && filtered.length === 0)
      ? `No NAV snapshots recorded within the last ${range === 'YTD' ? 'year-to-date' : range.toLowerCase()} window -- try a wider range.`
      : null;
    renderNavChart(state.currentModalFund, filtered, emptyMessage);
  }

  function renderNavChart(fund, history, emptyMessage) {
    const canvas = document.getElementById('modalNavCanvas');
    const wrapper = document.getElementById('modalNavChartWrapper');
    const subtitle = document.getElementById('modalNavSubtitle');
    if (!canvas || !wrapper) return;

    if (state.charts.modalNav) {
      state.charts.modalNav.destroy();
      state.charts.modalNav = null;
    }

    const existingNote = wrapper.querySelector('.chart-empty-note');
    if (existingNote) existingNote.remove();

    if (!history || history.length === 0) {
      canvas.style.display = 'none';
      if (subtitle) subtitle.textContent = 'No History Yet';
      const note = document.createElement('div');
      note.className = 'chart-empty-note absolute inset-0 flex items-center justify-center text-center text-[11px] text-[var(--color-text-subtle)] px-4';
      note.textContent = emptyMessage || 'No NAV history recorded yet for this fund. A real trend will build up here as the data pipeline runs over time.';
      wrapper.appendChild(note);
      return;
    }

    canvas.style.display = '';
    const isLight = document.documentElement.classList.contains('light');
    const isSingle = history.length === 1;
    if (subtitle) subtitle.textContent = isSingle ? '1 Snapshot Recorded' : `${history.length} Recorded Points`;

    const labels = history.map(h => h.nav_date);
    const values = history.map(h => h.nav);

    state.charts.modalNav = new Chart(canvas, {
      type: isSingle ? 'bar' : 'line',
      data: {
        labels,
        datasets: [{
          label: `${fund.fund_name} NAV (${fund.nav_currency || 'USD'})`,
          data: values,
          borderColor: '#2563eb',
          backgroundColor: isSingle ? '#2563eb' : 'rgba(37, 99, 235, 0.12)',
          fill: !isSingle,
          tension: 0.35,
          pointRadius: isSingle ? 0 : 3,
          pointHoverRadius: 6,
          maxBarThickness: 48,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: { grid: { display: false }, ticks: { display: false } },
          y: { grid: { color: isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)' }, ticks: { color: isLight ? '#64748b' : '#94a3b8', font: { size: 10 } } }
        }
      }
    });

    if (isSingle) {
      const note = document.createElement('div');
      note.className = 'chart-empty-note absolute bottom-1 right-2 text-[9px] text-[var(--color-text-subtle)] italic';
      note.textContent = 'Only one NAV snapshot recorded so far -- not enough history yet for a trend line.';
      wrapper.appendChild(note);
    }
  }

  // --------------------------------------------------------------------------
  // Load the fund
  // --------------------------------------------------------------------------
  async function loadFund() {
    const fundId = window.GIFT_FUND_ID;
    try {
      const res = await fetch(`/api/fund/${fundId}`);
      const data = await res.json();
      if (!data.success) return;

      const f = data.fund;
      state.currentModalFund = { id: f.fund_id, name: f.fund_name, nav: f.nav, currency: f.nav_currency || 'USD' };
      document.title = `${f.fund_name} | GIFT360`;
      setupBuyPanel(f);

      document.getElementById('modalFundName').textContent = f.fund_name;
      document.getElementById('modalAmcName').textContent = f.amc_name || 'GIFT City Asset Manager';
      document.getElementById('modalCategory').textContent = f.category || 'Specialized Investment Fund';

      const tierBadgeEl = document.getElementById('modalTierBadge');
      if (f.fund_flow_type === 'outbound') {
        tierBadgeEl.textContent = 'Outbound Fund';
        tierBadgeEl.className = 'text-xs px-3 py-1 rounded-full font-bold badge-outbound';
      } else if (f.fund_flow_type === 'inbound') {
        tierBadgeEl.textContent = 'Inbound Fund';
        tierBadgeEl.className = 'text-xs px-3 py-1 rounded-full font-bold badge-inbound';
      } else {
        tierBadgeEl.textContent = 'Not Yet Classified';
        tierBadgeEl.className = 'text-xs px-3 py-1 rounded-full font-bold badge-tier2';
      }

      document.getElementById('modalNav').textContent = f.nav !== null ? `${f.nav.toFixed(2)} ${f.nav_currency || 'USD'}` : 'Private / NFO Pending';
      document.getElementById('modalNavDate').textContent = f.nav_as_of ? `As of ${f.nav_as_of}` : (f.nav !== null ? 'Live Daily NAV' : 'Institutional Non-Public');

      const terEl = document.getElementById('modalTer');
      const terSubtitleEl = document.getElementById('modalTerSubtitle');
      if (f.expense_ratio !== null) {
        terEl.textContent = `${f.expense_ratio.toFixed(2)}%`;
        if (terSubtitleEl) terSubtitleEl.textContent = 'Direct Plan TER';
      } else if (f.fee_notes) {
        terEl.textContent = 'See Fee Schedule';
        if (terSubtitleEl) terSubtitleEl.textContent = 'TER not separately disclosed';
      } else {
        terEl.textContent = 'Not Publicly Disclosed';
        if (terSubtitleEl) terSubtitleEl.textContent = 'Direct Plan TER';
      }

      document.getElementById('modalLaunchDate').textContent = f.launch_date || 'Not Publicly Disclosed';
      document.getElementById('modalSourceLink').href = f.source_url;
      document.getElementById('modalSourceLink').textContent = f.source_name;

      const flowBadge = document.getElementById('modalFlowBadge');
      if (flowBadge) {
        flowBadge.textContent = f.source_tier === 'tier1_amc' ? 'Verified from official AMC source' : 'Sourced from fund directory listing';
        flowBadge.className = 'text-xs px-2.5 py-0.5 rounded-full font-bold badge-tier2';
        flowBadge.classList.remove('hidden');
      }

      const managerEl = document.getElementById('modalFundManager');
      if (managerEl) {
        if (f.fund_manager_name) {
          managerEl.textContent = `Fund Manager: ${f.fund_manager_name}`;
          managerEl.classList.remove('hidden');
        } else {
          managerEl.classList.add('hidden');
        }
      }

      const benchmarkEl = document.getElementById('modalBenchmark');
      if (benchmarkEl) {
        if (f.benchmark_index) {
          benchmarkEl.textContent = `Benchmark: ${f.benchmark_index}`;
          benchmarkEl.classList.remove('hidden');
        } else {
          benchmarkEl.classList.add('hidden');
        }
      }

      renderDataSections(f);

      let navHistory = [];
      try {
        const historyRes = await fetch(`/api/fund/${fundId}/nav-history`);
        const historyData = await historyRes.json();
        if (historyData.success) navHistory = historyData.nav_history;
      } catch (e) {
        console.error('Error fetching NAV history:', e);
      }
      state.fullNavHistory = navHistory;
      updateNavChart(state.navRange || 'ALL');
    } catch (e) {
      console.error('Error loading fund detail page:', e);
    }
  }

  document.querySelectorAll('.nav-range-tab').forEach(btn => {
    btn.addEventListener('click', () => updateNavChart(btn.getAttribute('data-range')));
  });

  loadFund();
});
