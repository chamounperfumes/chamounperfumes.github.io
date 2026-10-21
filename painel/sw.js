// Service worker do Painel Chamoun: serve só para os avisos (notificações no celular).
// Não guarda páginas em cache: o painel sempre abre a versão mais nova.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Painel Chamoun', {
    body: d.body || '', icon: 'icone-192.png', badge: 'icone-192.png', tag: d.tag || undefined,
    data: { url: d.url || './' },
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  e.waitUntil((async () => {
    const janelas = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of janelas) {
      if (c.url.startsWith(self.registration.scope)) {
        try { await c.navigate(url); } catch {}
        return c.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});
