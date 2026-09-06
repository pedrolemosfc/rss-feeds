# RSS feeds index

Generated: 2026-09-06 04:38 UTC

## Native feeds (not scraped)

- **Piauí**: https://piaui.uol.com.br/feed/ — native
- **Noize**: https://feeds.feedburner.com/noize — native
- **Ugly Things**: https://ugly-things.com/feed/ — native
- **Panenka**: https://www.panenka.org/feed/ — native (main covers all sections)
- **Treblezine**: https://www.treblezine.com/feed/ — native
- **Folha Ilustrada**: https://feeds.folha.uol.com.br/ilustrada/rss091.xml — native approximate for jazz/críticas/show topics
- **Guia Folha site-wide**: https://guia.folha.uol.com.br/rss.xml — native site-wide
- **Estadão Cultura**: https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/cultura/?body=%7B%22layout%22:%22google-news%22%7D — native section feed (not author-specific)
- **Veja SP site-wide**: https://vejasp.abril.com.br/feed/ — native site-wide (not column)
- **Correio site-wide**: https://www.correiobraziliense.com.br/feed/ — native site-wide (not author)
- **Anthropic News (RSSHub)**: https://rsshub.bestblogs.dev/anthropic/news — closest to Claude via RSSHub, unofficial

## Scraped feeds

- **folha-jazz** [OK] items=86 → `out/folha-jazz.xml`  source: https://www1.folha.uol.com.br/folha-topicos/jazz/  
  notes: scraped 86 items
- **folha-criticas-de-musica** [OK] items=46 → `out/folha-criticas-de-musica.xml`  source: https://www1.folha.uol.com.br/folha-topicos/criticas-de-musica/  
  notes: scraped 46 items
- **folha-show** [OK] items=53 → `out/folha-show.xml`  source: https://www1.folha.uol.com.br/folha-topicos/show/  
  notes: scraped 53 items
- **guia-restaurantes** [OK] items=78 → `out/guia-restaurantes.xml`  source: https://guia.folha.uol.com.br/restaurantes/  
  notes: scraped 78 items
- **guia-shows** [OK] items=97 → `out/guia-shows.xml`  source: https://guia.folha.uol.com.br/shows/  
  notes: scraped 97 items
- **estadao-sergio-martins** [OK] items=5 → `out/estadao-sergio-martins.xml`  source: https://www.estadao.com.br/cultura/sergio-martins/  
  notes: scraped 5 items
- **vejasp-tudo-de-som** [OK] items=30 → `out/vejasp-tudo-de-som.xml`  source: https://vejasp.abril.com.br/coluna/tudo-de-som/  
  notes: scraped 30 items
- **correio-irlam-rocha-lima** [OK] items=10 → `out/correio-irlam-rocha-lima.xml`  source: https://www.correiobraziliense.com.br/autor/irlam-rocha-lima/page/1/  
  notes: scraped 10 items
- **billboard-br-sergio-martins** [OK] items=20 → `out/billboard-br-sergio-martins.xml`  source: https://billboard.com.br/author/sergio-martins/  
  notes: scraped 20 items
- **asil-insights** [FAIL] items=0 → `out/asil-insights.xml`  source: https://asil.org/insights/  
  notes: fetch failed: HTTPError: HTTP Error 403: Forbidden
- **xai-news** [OK] items=84 → `out/xai-news.xml`  source: https://x.ai/news  
  notes: scraped 84 items
- **claude-blog** [OK] items=15 → `out/claude-blog.xml`  source: https://claude.com/blog  
  notes: scraped 15 items
- **espaco-unimed-agenda** [FAIL] items=0 → `out/espaco-unimed-agenda.xml`  source: https://www.espacounimed.com.br/agenda-de-shows/  
  notes: fetch failed: URLError: <urlopen error [Errno 101] Network is unreachable>

## Combined feeds

- **folha-musica-topicos** [OK] items=184 → `out/folha-musica-topicos.xml`  
  notes: merged 3 feeds -> 184 unique items (from ['folha-jazz', 'folha-criticas-de-musica', 'folha-show'])
- **guia-folha-restaurantes-shows** [OK] items=175 → `out/guia-folha-restaurantes-shows.xml`  
  notes: merged 2 feeds -> 175 unique items (from ['guia-restaurantes', 'guia-shows'])
