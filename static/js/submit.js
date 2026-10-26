const form = document.getElementById('request-form');
const portfolioInput = document.getElementById('portfolioUrl');
const recordTypeSelect = document.getElementById('recordType');
const advanced = document.getElementById('advanced-target');
const targetInput = document.getElementById('recordValue');
const targetHint = document.getElementById('target-hint');
const targetWarning = document.getElementById('target-warning');
const allowedNode = document.getElementById('allowed-cnames');

if (form && portfolioInput && recordTypeSelect && targetInput && targetHint && targetWarning && allowedNode) {
  const ALLOWED = JSON.parse(allowedNode.textContent);
  const CNAME_HINT =
    'We fill this in from your portfolio URL. Only change it if your host gave you a specific target. Enter the hostname only, with no <code>https://</code> and no path.';
  const MANUAL_PLACEHOLDER = {
    A: '203.0.113.10',
    AAAA: '2001:db8::1',
    TXT: 'verify=abc123',
  };
  let targetEdited = targetInput.value.trim().length > 0;

  const recordType = () => recordTypeSelect.value.toUpperCase();

  const hostnameFromUrl = (value) => {
    try {
      return new URL(value.trim()).hostname.toLowerCase().replace(/\.$/, '');
    } catch {
      return '';
    }
  };

  const isAllowedCnameTarget = (host) => {
    const value = host.trim().toLowerCase().replace(/\.$/, '');
    if (!value) return false;
    return ALLOWED.some((suffix) => value === suffix || value.endsWith(`.${suffix}`));
  };

  const updateTargetWarning = () => {
    const value = targetInput.value.trim();
    if (recordType() === 'CNAME' && value && !isAllowedCnameTarget(value)) {
      targetWarning.innerHTML =
        'This target is not on our supported hosts list, so the request will be rejected. See <a href="/guide/troubleshooting">Troubleshooting</a>.';
      targetWarning.hidden = false;
    } else {
      targetWarning.hidden = true;
      targetWarning.textContent = '';
    }
  };

  const syncTargetFromPortfolio = () => {
    if (targetEdited || recordType() !== 'CNAME') return;
    const host = hostnameFromUrl(portfolioInput.value);
    targetInput.value = host.includes('.') ? host : '';
    updateTargetWarning();
  };

  const applyRecordType = () => {
    if (recordType() === 'CNAME') {
      targetInput.placeholder = 'juan-dela-cruz.github.io';
      targetHint.innerHTML = CNAME_HINT;
      syncTargetFromPortfolio();
    } else {
      if (!targetEdited) targetInput.value = '';
      targetInput.placeholder = MANUAL_PLACEHOLDER[recordType()] ?? '';
      targetHint.textContent = `Enter the ${recordType()} value your host gave you.`;
      if (advanced) advanced.open = true;
      targetWarning.hidden = true;
    }
  };

  portfolioInput.addEventListener('input', syncTargetFromPortfolio);
  recordTypeSelect.addEventListener('change', () => {
    targetEdited = false;
    applyRecordType();
  });
  targetInput.addEventListener('input', () => {
    targetEdited = true;
    updateTargetWarning();
  });

  applyRecordType();
}
