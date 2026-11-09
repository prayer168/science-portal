const origin = 'https://prayer168.github.io';
const taipeiDate = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Taipei' });
const browserIdPattern = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/;

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== '/visit') return new Response(null, { status: 404 });
    if (request.headers.get('Origin') !== origin) return new Response(null, { status: 403 });

    const headers = {
      'Access-Control-Allow-Origin': origin,
      'Cache-Control': 'no-store',
      'Vary': 'Origin'
    };
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: { ...headers, 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' }
      });
    }
    if (request.method !== 'POST') {
      return new Response(null, { status: 405, headers: { ...headers, Allow: 'POST, OPTIONS' } });
    }

    const body = await request.json().catch(() => null);
    const browserId = body?.browserId;
    if (typeof browserId !== 'string' || !browserIdPattern.test(browserId)) {
      return new Response(null, { status: 400, headers });
    }

    const day = taipeiDate.format(new Date());
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(browserId));
    const browserKey = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');

    try {
      const [, total] = await env.VISITS.batch([
        env.VISITS.prepare(
          'INSERT INTO browsers (id, last_day) VALUES (?, ?) ' +
          'ON CONFLICT(id) DO UPDATE SET last_day = excluded.last_day ' +
          'WHERE browsers.last_day < excluded.last_day'
        ).bind(browserKey, day),
        env.VISITS.prepare('SELECT count, started_on AS startedOn FROM totals WHERE id = 1')
      ]);
      return Response.json(total.results[0], { headers });
    } catch (error) {
      console.error('Visitor counter unavailable', error);
      return new Response(null, { status: 503, headers });
    }
  }
};
