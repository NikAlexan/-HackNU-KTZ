    const WS_URL = 'ws://localhost:8000/ws/loco/data';
    const frame = document.getElementById('frame');
    const topBar = document.getElementById('top');
    const statusText = document.getElementById('statusText');

    let currentView = '/electro-driver-dashboard';
    let retryTimer = null;

    function setStatus(kind, text) {
      topBar.classList.remove('ok', 'err');
      if (kind === 'ok') topBar.classList.add('ok');
      if (kind === 'err') topBar.classList.add('err');
      statusText.textContent = text;
    }

    function normalizeTypeValue(v) {
      const t = String(v ?? '').toLowerCase().trim();
      if (!t) return null;
      if (t.includes('electro') || t.includes('electric') || t.includes('kz8a') || t.includes('type-electro') || t === '1' || t === '1.0') return 'electro';
      if (t.includes('diesel') || t.includes('te33a') || t.includes('type-diesel') || t === '0' || t === '0.0') return 'diesel';
      return null;
    }

    function deepFindType(obj, depth = 0) {
      if (!obj || depth > 5) return null;

      if (typeof obj === 'string') return normalizeTypeValue(obj);

      if (Array.isArray(obj)) {
        for (const item of obj) {
          const t = deepFindType(item, depth + 1);
          if (t) return t;
        }
        return null;
      }

      if (typeof obj !== 'object') return null;

      const direct = normalizeTypeValue(obj.type)
        || normalizeTypeValue(obj.series)
        || normalizeTypeValue(obj.loco_id)
        || normalizeTypeValue(obj.locomotiveType)
        || normalizeTypeValue(obj.engine_type)
        || normalizeTypeValue(obj.kind);
      if (direct) return direct;

      for (const v of Object.values(obj)) {
        const t = deepFindType(v, depth + 1);
        if (t) return t;
      }
      return null;
    }

    function extractTypeFromMessage(messageData) {
      // messageData may be JSON string, plain text like "type:diesel", object, or array.
      if (typeof messageData === 'string') {
        const raw = messageData.toLowerCase();

        // Priority: explicit "type:diesel" / "type=diesel"
        if (/type\s*[:=]\s*["']?\s*diesel\b/i.test(raw)) return 'diesel';
        if (/type\s*[:=]\s*["']?\s*electro\b/i.test(raw)) return 'electro';

        // Fallback: any diesel/electro hint in plain text payload
        if (raw.includes('diesel') || raw.includes('te33a')) return 'diesel';
        if (raw.includes('electro') || raw.includes('electric') || raw.includes('kz8a')) return 'electro';

        // Try JSON parse only after raw checks
        try {
          return deepFindType(JSON.parse(messageData));
        } catch (_e) {
          return null;
        }
      }
      return deepFindType(messageData);
    }

    function routeByType(type) {
      const next = type === 'diesel' ? '/diesel-dispatcher-dashboard' : '/electro-driver-dashboard';
      if (next !== currentView) {
        currentView = next;
        frame.src = next;
      }
    }

    function connect() {
      setStatus('', 'connecting...');
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => setStatus('ok', 'connected');
      ws.onmessage = (event) => {
        const type = extractTypeFromMessage(event.data);
        if (type) {
          routeByType(type);
          statusText.textContent = 'connected • type=' + type;
        }
      };
      ws.onclose = () => {
        setStatus('err', 'reconnecting...');
        if (retryTimer) clearTimeout(retryTimer);
        retryTimer = setTimeout(connect, 1500);
      };
      ws.onerror = () => {
        try { ws.close(); } catch (_e) {}
      };
    }

    connect();
  
