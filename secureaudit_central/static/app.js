'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
let token = sessionStorage.getItem('secureaudit-key') || '';
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('key')) { token = fragment.get('key'); history.replaceState(null, '', location.pathname); }
let endpoints = [], jobs = [], activeEndpoint = null, lastSummary = {}, currentView = 'overview', timer = null, refreshing = false;
const date = value => value ? new Date(value).toLocaleString(undefined, {month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
const pct = value => value == null ? '—' : `${Number(value).toFixed(1)}%`;
function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error-text', error); $('message').hidden = false; }
function locked(text = '') { clearInterval(timer); token = ''; sessionStorage.removeItem('secureaudit-key'); $('workspace').hidden = true; $('login').hidden = false; $('login-error').textContent = text; }
async function api(path, data, raw = false) {
  const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', headers: {'Authorization':`Bearer ${token}`, ...(data === undefined ? {} : {'Content-Type':'application/json'})}, ...(data === undefined ? {} : {body:JSON.stringify(data)})});
  if (response.status === 401) { locked('Access key not accepted. Reopen the dashboard from the launcher.'); throw new Error('Access key not accepted'); }
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}). Check the input format.`); }
  return raw ? response.blob() : response.json();
}
async function action(button, fn) { button.disabled = true; try { await fn(); } catch (err) { message(err.message, true); } finally { button.disabled = false; } }
function download(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function renderStats(summary) {
  lastSummary = summary;
  $('total').textContent = summary.endpoint_count;
  $('nav-count').textContent = summary.endpoint_count;
  $('source-stat').textContent = `${summary.simulated_count} simulated · ${summary.endpoint_count-summary.simulated_count} registered`;
  $('score').textContent = pct(summary.score); $('coverage').textContent = pct(summary.coverage);
  $('risk').textContent = summary.at_risk_endpoints; $('risk-stat').textContent = `${summary.assessed_endpoints} endpoints have evidence`;
  $('passed').textContent = summary.passed; $('failed').textContent = summary.failed; $('errors').textContent = summary.errors;
  $('db-type').textContent = summary.database === 'postgresql' ? 'PostgreSQL' : 'SQLite · local';
  const total = summary.passed + summary.failed + summary.errors, circumference = 2 * Math.PI * 75;
  $('ring-total').textContent = total;
  let offset = 0;
  for (const [id, count] of [['ring-pass',summary.passed],['ring-fail',summary.failed],['ring-error',summary.errors]]) {
    const length = total ? count / total * circumference : 0;
    $(id).setAttribute('stroke-dasharray', `${length} ${circumference-length}`);
    $(id).setAttribute('stroke-dashoffset', String(-offset)); offset += length;
  }
  $('scan').disabled = !summary.simulated_count; $('schedule').disabled = !summary.simulated_count;
  $('local-scan').disabled = jobs.some(job => job.kind === 'local' && ['queued','running'].includes(job.status));
}
function renderEndpoints() {
  const term = $('search').value.toLowerCase(), source = $('source-filter').value, posture = $('risk-filter').value;
  const filtered = endpoints.filter(e => `${e.hostname} ${e.group_name}`.toLowerCase().includes(term) && (source === 'all' || (source === 'demo' ? e.simulated : !e.simulated)) && (posture === 'all' || (posture === 'pending' ? !e.latest : posture === 'failed' ? e.latest?.failed > 0 : e.latest?.errors > 0)));
  $('inventory-count').textContent = endpoints.length; $('visible-count').textContent = `${filtered.length} of ${endpoints.length} endpoints`;
  $('endpoint-rows').innerHTML = filtered.length ? filtered.map(e => {
    const a = e.latest, findings = a ? `${a.failed} fail · ${a.errors} error` : 'Awaiting evidence';
    return `<tr><td><button data-endpoint="${esc(e.id)}">${esc(e.hostname)}</button></td><td>${esc(e.group_name)}</td><td><span class="source-tag ${e.simulated?'demo':''}">${e.simulated?'Simulated':a?.source==='local-scanner'?'Local scanner':'Registered'}</span></td><td class="${a?.failed?'score-bad':'score-good'}">${pct(a?.score)}</td><td>${pct(a?.coverage)}</td><td>${findings}</td><td>${date(a?.collected_at)}</td><td><button data-endpoint="${esc(e.id)}">Inspect ↗</button></td></tr>`;
  }).join('') : '<tr><td colspan="8" class="empty"><strong>No endpoints in this view.</strong>Create the demo fleet, scan this PC, or register an endpoint to import evidence.</td></tr>';
}
function renderJobs() {
  const names = new Map(endpoints.map(e => [e.id,e.hostname]));
  $('queued-count').textContent = `${jobs.filter(j => ['queued','running'].includes(j.status)).length} active`;
  $('done-count').textContent = `${jobs.filter(j => j.status === 'completed').length} completed`;
  $('job-rows').innerHTML = jobs.length ? jobs.map(j => `<tr><td>${esc(names.get(j.endpoint_id)||j.endpoint_id)} <span class="source-tag ${j.kind==='demo'?'demo':''}">${j.kind==='local'?'Local':'Demo'}</span></td><td>${esc(j.id.slice(0,8))}</td><td><span class="status ${esc(j.status)}">${esc(j.status)}</span></td><td>${date(j.due_at)}</td><td>${date(j.completed_at)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty"><strong>No assessment jobs yet.</strong>Schedule the demo fleet or scan this PC.</td></tr>';
}
function renderEvents(events) { $('activity-rows').innerHTML = events.length ? events.map(e => `<div class="activity-row"><time>${date(e.at)}</time><strong>${esc(e.action)}</strong><span>${esc(e.detail)}</span></div>`).join('') : '<p class="empty">Workspace operations will appear here.</p>'; }
async function refresh() {
  if (refreshing || !token) return;
  refreshing = true;
  try {
    const [fleet, queue, summary, events] = await Promise.all(['/api/endpoints','/api/jobs','/api/summary','/api/events'].map(path => api(path)));
    endpoints = fleet; jobs = queue; renderStats(summary); renderEndpoints(); renderJobs(); renderEvents(events);
    $('last-updated').textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (err) { if (token) message(`Unable to refresh: ${err.message}`, true); }
  finally { refreshing = false; }
}
async function connect() {
  await api('/api/summary');
  sessionStorage.setItem('secureaudit-key',token); $('login').hidden = true; $('workspace').hidden = false;
  await refresh(); clearInterval(timer); timer = setInterval(refresh,2000);
}
function setView(view) {
  currentView = view;
  const names = {overview:['Overview','Your security posture, in focus.','A central workspace for endpoint evidence and assessment history.'],endpoints:['Endpoints','Every endpoint. Every finding.','Explore your inventory and inspect the evidence behind each result.'],jobs:['Assessment queue','Assessments, on your schedule.','Follow queued, running, and completed assessments in one place.'],activity:['Activity trail','A record of workspace operations.','Registration, job scheduling, and evidence collection events.']};
  $('page-name').textContent = names[view][0]; $('view-title').textContent = names[view][1]; $('view-subtitle').textContent = names[view][2];
  for (const key of ['overview','jobs','activity']) $(`${key}-view`).hidden = key !== view;
  $('endpoint-section').hidden = !['overview','endpoints'].includes(view);
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active',button.dataset.view === view));
  window.scrollTo({top:0,behavior:'instant'});
}
async function queueFleet(delay) {
  const ids = endpoints.filter(e=>e.simulated).map(e=>e.id);
  if (!ids.length) throw new Error('Create a demo fleet first.');
  const result = await api('/api/demo/jobs',{endpoint_ids:ids,delay_seconds:delay});
  message(`${result.count} synthetic assessments scheduled for ${date(result.due_at)}. Evidence will arrive as jobs complete.`);
  setView('jobs'); await refresh();
}
function showAssessment(assessment) {
  $('assessment-body').innerHTML = `<p>Collected ${date(assessment.collected_at)} · Score ${pct(assessment.score)} · Coverage ${pct(assessment.coverage)} · Source: ${esc(assessment.source)}</p><p class="hash">SHA-256: ${esc(assessment.sha256)}</p>${assessment.checks.map(c=>`<article class="evidence-check"><h3><span>${esc(c.check_id)} · ${esc(c.title)}</span><span class="status ${esc(c.status)}">${esc(c.status)}</span></h3><pre>${esc(c.detail)}</pre></article>`).join('')}`;
}
async function inspect(id) {
  activeEndpoint = endpoints.find(e=>e.id===id);
  if (!activeEndpoint) return;
  $('evidence-title').textContent = activeEndpoint.hostname;
  $('evidence-source').textContent = activeEndpoint.simulated ? 'SIMULATED ENDPOINT · Synthetic fixtures only; no physical device was scanned.' : 'REGISTERED ENDPOINT · Local scanner or imported evidence. Administrative privileges affect collection coverage.';
  const assessments = await api(`/api/endpoints/${id}/history`);
  $('evidence-content').innerHTML = assessments.length ? `<select id="history-picker" class="history-picker" aria-label="Assessment history">${assessments.map((a,i)=>`<option value="${i}">${date(a.collected_at)} · ${esc(a.submission_id)}</option>`).join('')}</select><div id="assessment-body"></div>` : '<p class="empty">No evidence yet. Import a central evidence JSON file, or use Scan this PC for the current machine.</p>';
  if (assessments.length) { showAssessment(assessments[0]); $('history-picker').addEventListener('change',e=>showAssessment(assessments[Number(e.target.value)])); }
  if (!$('evidence-dialog').open) $('evidence-dialog').showModal();
}
$('login-form').addEventListener('submit', async e=>{e.preventDefault(); token=$('key').value.trim(); try { await connect(); $('key').value=''; } catch(err) { $('login-error').textContent=err.message; }});
$('signout').addEventListener('click',()=>locked());
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>$(button.dataset.close).close()));
for (const id of ['search','source-filter','risk-filter']) $(id).addEventListener(id==='search'?'input':'change',renderEndpoints);
$('endpoint-rows').addEventListener('click', e=>{const button=e.target.closest('[data-endpoint]'); if(button) inspect(button.dataset.endpoint).catch(err=>message(err.message,true));});
$('seed').addEventListener('click',()=>action($('seed'),async()=>{const result=await api('/api/demo/seed',{count:100}); message(`${result.created} simulated endpoints created. Click Assess demo fleet to collect synthetic evidence.`); await refresh();}));
$('scan').addEventListener('click',()=>action($('scan'),()=>queueFleet(0)));
$('schedule').addEventListener('click',()=>$('schedule-dialog').showModal());
$('schedule-form').addEventListener('submit',e=>{e.preventDefault(); action(e.submitter,async()=>{await queueFleet(Number($('delay').value)); $('schedule-dialog').close();});});
$('register').addEventListener('click',()=>$('register-dialog').showModal());
$('register-form').addEventListener('submit',e=>{e.preventDefault(); action(e.submitter,async()=>{const result=await api('/api/endpoints',{hostname:$('hostname').value.trim(),group_name:$('group').value.trim()||'Unassigned'}); $('register-dialog').close(); e.target.reset(); message(`${result.hostname} registered. Open it to import evidence.`); await refresh(); await inspect(result.id);});});
$('local-scan').addEventListener('click',()=>action($('local-scan'),async()=>{const result=await api('/api/local/scan',{}); message(`Local scan queued for ${result.hostname}. Your five approved PowerShell checks run without changing settings. Run the launcher as Administrator for privileged checks.`); setView('jobs'); await refresh();}));
$('import-file').addEventListener('change',async e=>{
  const file=e.target.files[0]; if(!file||!activeEndpoint)return;
  try { if(file.size>2_000_000)throw new Error('Evidence file must be smaller than 2 MB.'); const payload=JSON.parse(await file.text()); const result=await api(`/api/endpoints/${activeEndpoint.id}/evidence`,payload); message(result.created?'Evidence imported successfully.':'This identical submission was already recorded.'); await refresh(); await inspect(activeEndpoint.id); }
  catch(err){$('evidence-dialog').close();message(`Import failed: ${err.message}`,true);}finally{e.target.value='';}
});
$('sample').addEventListener('click',()=>download(new Blob([JSON.stringify({submission_id:crypto.randomUUID(),collected_at:new Date().toISOString(),checks:[{check_id:'WIN-FW-001',title:'Windows Firewall Enabled',status:'Pass',detail:'EXAMPLE ONLY: Replace this with actual collected evidence before importing.',severity:'High'}]},null,2)],{type:'application/json'}),'central-evidence-example.json'));
$('export-json').addEventListener('click',()=>action($('export-json'),async()=>{const data=await api('/api/export'); download(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),'SecureAudit-evidence.json'); message('Evidence JSON exported with source labels and SHA-256 hashes.');}));
$('export-csv').addEventListener('click',()=>action($('export-csv'),async()=>download(await api('/api/export.csv',undefined,true),'SecureAudit-summary.csv')));
$('report').addEventListener('click',()=>{setView('overview'); window.print();});
if(token)connect().catch(err=>locked(err.message));
