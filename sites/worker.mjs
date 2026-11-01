// Sites dispatch enforces owner-private access on every path, including data/API.
// Do not widen the audience until write authorization has been designed separately.
const MAX_BODY = 2_000_000;
const fail = (code, status = 422) => { throw Object.assign(new Error(code), {status}); };
const canonical = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
export async function digest(value) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(value)));
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
}
const researchHash = settings => digest(Object.fromEntries(['fields','sites','languages'].map(key => [key, settings[key]])));
const sameKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join() === [...keys].sort().join();
const nonempty = (value, max = 10000) => typeof value === 'string' && !!value.trim() && value.length <= max;
const timestamp = value => typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));

export function validateSettings(settings, initial) {
  if (!sameKeys(settings, ['version','fields','sites','languages','limits','displaySettings']) || !Number.isInteger(settings.version) || settings.version < 1
    || canonical(settings.languages) !== '["ja"]' || canonical(settings.limits) !== canonical(initial.settings.limits)) fail('INVALID_SETTINGS');
  const limits = settings.limits, ids = new Set(), names = new Set();
  if (!Array.isArray(settings.fields) || !settings.fields.length || settings.fields.length > limits.maxFields) fail('INVALID_FIELDS');
  for (const field of settings.fields) {
    if (!sameKeys(field, ['fieldId','name','instructions','active']) || !nonempty(field.fieldId,100) || ids.has(field.fieldId)
      || !nonempty(field.name,limits.maxNameLength) || names.has(field.name) || field.name === 'X'
      || !nonempty(field.instructions,limits.maxInstructionsLength) || typeof field.active !== 'boolean') fail('INVALID_FIELD');
    ids.add(field.fieldId); names.add(field.name);
  }
  if (!settings.fields.some(field => field.active)) fail('ACTIVE_FIELD_REQUIRED');
  if (!Array.isArray(settings.sites) || settings.sites.length > 100) fail('INVALID_SITES');
  ids.clear();
  for (const site of settings.sites) {
    if (!sameKeys(site, ['siteId','name','url','active']) || !nonempty(site.siteId,100) || ids.has(site.siteId)
      || !nonempty(site.name,100) || typeof site.active !== 'boolean') fail('INVALID_SITE');
    let url; try { url = new URL(site.url); } catch { fail('INVALID_SITE_URL'); }
    if (url.protocol !== 'https:' || url.port && url.port !== '443' || url.username || url.password || !url.hostname.includes('.') || url.hostname.endsWith('.')
      || /^(localhost|127\.|0\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)/i.test(url.hostname)
      || url.hostname.includes(':') || /\.(local|localhost|internal)$/i.test(url.hostname)) fail('INVALID_SITE_URL');
    ids.add(site.siteId);
  }
  const options = initial.display.settingsOptions;
  if (!sameKeys(settings.displaySettings, Object.keys(options)) || Object.entries(options).some(([key, choices]) => !choices.includes(settings.displaySettings[key]))) fail('INVALID_DISPLAY_SETTINGS');
}

export async function viewNews(news, settings, period, initial) {
  if (!['24h','7d'].includes(period)) fail('INVALID_PERIOD');
  const cfg = {...initial.display, ...settings.displaySettings};
  cfg.pageSize = Math.max(cfg.pageSize, cfg.minTopicsPerField);
  cfg.fields = settings.fields.filter(field => field.active).map(field => field.name);
  cfg.aliases = Object.fromEntries(Object.entries(cfg.aliases).filter(([, name]) => cfg.fields.includes(name)));
  for (const field of settings.fields.filter(field => field.active)) cfg.aliases[field.fieldId] = field.name;
  let excludedTopicCount = 0;
  const topics = [], fieldCoverage = [];
  for (const field of cfg.fields) {
    const group = news.periods[period].topics.filter(topic => topic.field === field).sort((a,b) =>
      (b.globalImportanceScore || b.observedAttentionScore || 0) - (a.globalImportanceScore || a.observedAttentionScore || 0)
      || (a.topicId < b.topicId ? -1 : a.topicId > b.topicId ? 1 : 0));
    const shown = group.filter((topic, i) => i < cfg.minTopicsPerField || (topic.globalImportanceScore || 0) > cfg.additionalThreshold);
    topics.push(...shown); excludedTopicCount += group.length - shown.length;
    fieldCoverage.push({field, shortfall: Math.max(0, cfg.minTopicsPerField - shown.length)});
  }
  const {periods, ...metadata} = news;
  return {...metadata, topics, displayConfig: cfg, fieldCoverage, excludedTopicCount,
    collectionSites: settings.sites.filter(site => site.active),
    reportingWindowStart: news.referenceAt ? new Date(Date.parse(news.referenceAt) - initial.scoring.reportingHours * 3600000).toISOString() : null,
    reportingWindowEnd: news.referenceAt || null, settingsChanged: !!news.settingsHash && news.settingsHash !== await researchHash(settings)};
}

// Research and scoring remain in Python. This boundary accepts only a prepared,
// settings-matched news file and refuses shortfalls before replacing the R2 object.
export async function validateNews(news, settings, initial) {
  if (news?.version !== 1 || !sameKeys(news.periods, ['24h','7d']) || news.periodBasis !== 'article_published_at'
    || news.settingsHash !== await researchHash(settings) || canonical(news.scoringConfig) !== canonical(initial.scoring)
    || !['referenceAt','generatedAt','executionStartedAt','executionCompletedAt'].every(key => timestamp(news[key]))
    || Date.parse(news.generatedAt) !== Date.parse(news.executionCompletedAt)
    || Date.parse(news.executionStartedAt) > Date.parse(news.executionCompletedAt)
    || Date.parse(news.referenceAt) > Date.parse(news.executionCompletedAt)
    || !Array.isArray(news.limitations) || news.limitations.some(item => typeof item !== 'string')) fail('INVALID_NEWS_FILE');
  const reference = Date.parse(news.referenceAt);
  for (const [period, hours] of [['24h',24],['7d',168]]) {
    const topics = news.periods[period]?.topics, ids = new Set();
    if (!Array.isArray(topics)) fail('INVALID_TOPICS');
    for (const topic of topics) {
      if (!nonempty(topic.topicId) || ids.has(topic.topicId) || !nonempty(topic.title) || !nonempty(topic.summary)
        || !settings.fields.some(field => field.name === topic.field) || !topic.details || !Array.isArray(topic.missingMetrics)
        || !Number.isFinite(topic.dataCompleteness) || topic.dataCompleteness < 0 || topic.dataCompleteness > 1
        || !Array.isArray(topic.sources) || !topic.sources.some(source => source.verificationStatus === 'verified' && nonempty(source.title)
          && source.publishedAt?.includes('T') && Date.parse(source.publishedAt) > reference - hours * 3600000
          && Date.parse(source.publishedAt) <= reference && !['api','reaction','attention'].includes(source.sourceType))) fail('INVALID_TOPIC_FILE');
      for (const key of ['globalImportanceScore','observedAttentionScore']) if (topic[key] != null && (!Number.isFinite(topic[key]) || topic[key] < 0 || topic[key] > 100)) fail('INVALID_SCORE');
      ids.add(topic.topicId);
    }
    for (const field of settings.fields.filter(field => field.active)) if (topics.filter(topic => topic.field === field.name).length < settings.displaySettings.minTopicsPerField) fail('NEWS_UPDATE_HELD',409);
  }
}

export function createApp(initial) {
  return {async fetch(request, env) {
    const headers = {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
      'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"};
    const json = (status, value) => new Response(JSON.stringify(value), {status, headers:{...headers,'Content-Type':'application/json; charset=utf-8'}});
    try {
      const url = new URL(request.url), path = url.pathname;
      // Cross-site links and OAuth redirects are valid read navigations. Sites
      // dispatch still authenticates them. CSRF checks apply to writes only.
      const mutation = !['GET','HEAD'].includes(request.method);
      if (mutation && (request.headers.get('Origin') && request.headers.get('Origin') !== url.origin || request.headers.get('Sec-Fetch-Site') === 'cross-site')) return json(403,{error:'INVALID_ORIGIN'});
      if (request.method === 'GET' && Object.hasOwn(initial.assets,path)) return new Response(initial.assets[path].body,{headers:{...headers,'Content-Type':initial.assets[path].type}});
      if (!env.BUCKET) return json(503,{error:'SITES_STORAGE_UNAVAILABLE'});
      const stored = await env.BUCKET.get('state.json');
      const state = stored ? await stored.json() : {settings:initial.settings,news:initial.news,researchStatus:initial.researchStatus};
      if (request.method === 'GET') {
        if (path === '/data/news.json') return json(200,state.news);
        if (path !== '/api/state') return json(404,{error:'NOT_FOUND'});
        const user = request.headers.get('oai-authenticated-user-id');
        const savedPreferences = user ? await env.BUCKET.get('preferences/'+encodeURIComponent(user)+'.json') : null;
        const payload = {settings:state.settings,preferences:savedPreferences ? await savedPreferences.json() : {knownTermIds:[]},
          revision:await digest(state.settings),news:await viewNews(state.news,state.settings,url.searchParams.get('period') || '24h',initial),researchStatus:state.researchStatus};
        payload.stateHash = await digest(payload);
        return json(200,payload);
      }
      if (request.method !== 'PUT') return json(405,{error:'METHOD_NOT_ALLOWED'});
      if (!['/api/news','/api/settings','/api/preferences'].includes(path)) return json(404,{error:'NOT_FOUND'});
      if (request.headers.get('Content-Type')?.split(';')[0] !== 'application/json') return json(415,{error:'JSON_REQUIRED'});
      if (+request.headers.get('Content-Length') > MAX_BODY) return json(413,{error:'BODY_TOO_LARGE'});
      // Limit streamed/chunked bodies too, before decoding or parsing.
      const reader = request.body?.getReader(), chunks = []; let size = 0;
      if (!reader) fail('EMPTY_BODY');
      for (;;) { const {done,value} = await reader.read(); if (done) break; size += value.length; if (size > MAX_BODY) {await reader.cancel(); return json(413,{error:'BODY_TOO_LARGE'});} chunks.push(value); }
      const bytes = new Uint8Array(size); let offset = 0; for (const chunk of chunks) {bytes.set(chunk,offset);offset += chunk.length;}
      let payload; try {payload = JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));} catch {fail('INVALID_JSON');}
      if (path === '/api/preferences') {
        const user = request.headers.get('oai-authenticated-user-id');
        if (!user) return json(403,{error:'USER_IDENTITY_REQUIRED'});
        const ids = payload?.knownTermIds;
        if (!sameKeys(payload,['knownTermIds']) || !Array.isArray(ids) || ids.length > 10000 || ids.some(id => !nonempty(id,200)) || new Set(ids).size !== ids.length) fail('INVALID_KNOWN_TERMS');
        await env.BUCKET.put('preferences/'+encodeURIComponent(user)+'.json',JSON.stringify(payload));
        return json(200,payload);
      }
      if (!sameKeys(payload,path === '/api/news' ? ['revision','news'] : ['revision','settings'])) fail('INVALID_REQUEST');
      if (payload.revision !== await digest(state.settings)) return json(409,{error:'設定が更新されています。再読込してください。'});
      if (path === '/api/settings') {validateSettings(payload.settings,initial);state.settings = {...payload.settings,version:state.settings.version+1};}
      else {
        await validateNews(payload.news,state.settings,initial);
        if (Date.parse(payload.news.generatedAt) < Date.parse(state.news.generatedAt)) fail('OLDER_NEWS_REJECTED',409);
        state.news = payload.news;state.researchStatus = null;
      }
      // Conditional writes prevent a concurrent update from overwriting settings/news.
      const saved = await env.BUCKET.put('state.json',JSON.stringify(state),{onlyIf:stored ? {etagMatches:stored.etag} : {etagDoesNotMatch:'*'}});
      if (!saved) return json(409,{error:'CONCURRENT_UPDATE'});
      return json(200,path === '/api/settings' ? {revision:await digest(state.settings),settings:state.settings} : {generatedAt:state.news.generatedAt});
    } catch (error) {return json(error.status || 500,{error:error.status ? error.message : 'SITES_DATA_UNAVAILABLE'});}
  }};
}
