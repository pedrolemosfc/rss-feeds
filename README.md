# RSS feeds

Feeds scrapados e atualizados automaticamente via **GitHub Actions** (a cada 6 horas), sem depender de bots externos.

> **Readwise Reader:** use os links **jsDelivr** abaixo (Content-Type `application/xml`). O `raw.githubusercontent.com` manda `text/plain` e o Reader costuma falhar ou não atualizar.

## Feeds scrapados (cole no leitor)

| Fonte | Feed |
|------|------|
| Folha — Jazz + Críticas + Show (junto) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/folha-musica-topicos.xml |
| Guia Folha — Restaurantes + Shows (junto) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/guia-folha-restaurantes-shows.xml |
| Estadão — Sérgio Martins | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/estadao-sergio-martins.xml |
| Veja SP — Tudo de Som | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/vejasp-tudo-de-som.xml |
| Correio Braziliense — Irlam Rocha Lima | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/correio-irlam-rocha-lima.xml |
| Billboard Brasil — Sérgio Martins | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/billboard-br-sergio-martins.xml |
| ASIL Insights | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/asil-insights.xml |
| xAI News | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/xai-news.xml |
| Claude Blog | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/claude-blog.xml |
| Espaço Unimed — Agenda de shows | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/espaco-unimed-agenda.xml |
| Page9 — Artes | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/page9-artes.xml |
| Musicalidade | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/musicalidade.xml |
| Qobuz Magazine BR | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/qobuz-magazine-br.xml |
| NOIZE | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/noize.xml |
| Treblezine | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/treblezine.xml |
| Estado da Arte (Estadão) — todas as seções | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/estado-da-arte.xml |

### Também disponíveis (seções individuais)

| Fonte | Feed |
|------|------|
| Folha Jazz | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/folha-jazz.xml |
| Folha Críticas de música | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/folha-criticas-de-musica.xml |
| Folha Show | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/folha-show.xml |
| Guia Restaurantes | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/guia-restaurantes.xml |
| Guia Shows | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/guia-shows.xml |

## Feeds nativos (não passam por este repo)

- Piauí: https://piaui.uol.com.br/feed/
- Ugly Things: https://ugly-things.com/feed/
- Panenka: https://www.panenka.org/feed/
- good-music.kiev.ua (junto): https://www.rssrssrssrss.com/api/merge?url=http%3A%2F%2Fgood-music.kiev.ua%2Fnews%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fload%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fpubl%2Frss%2F


## Nativos deste lote

Sites com RSS nativo usable — **não** são scrapados neste repo; use direto:

- **TIME** (todas as seções num feed): https://time.com/feed/
- **ISMO** (Ghost principal cobre as seções): https://www.ismo.mov/rss/

> **Nota:** feeds nativos de **NOIZE** (Feedburner / site) e **Treblezine** (`/feed/`) eram unreliable no Readwise Reader — agora há scrapes via WP REST na tabela acima (jsDelivr).

> **Nota:** o nativo `https://estadodaarte.estadao.com.br/feed/` existe mas traz só ~10 itens; o scrape via WP REST na tabela acima cobre todas as seções (jsDelivr).


## Casas de show / venues (jsDelivr)

Um item RSS por show/evento anunciado. Espelhos nativos e scrapes; Content-Type `application/xml` via jsDelivr.

| Venue | Feed |
|------|------|
| Nubank Parque — Shows (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/nubank-parque-shows.xml |
| Terra SP (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/terra-sp.xml |
| MIS-SP — Eventos (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/mis-sp.xml |
| Teatro B32 (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/teatro-b32.xml |
| Tokio Marine Hall (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/tokio-marine-hall.xml |
| Casa Natura Musical — Eventos (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/casa-natura-musical.xml |
| Guarulhos Cultural (nativo espelhado) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/guarulhos-cultural.xml |
| Concerto revista (nativo espelhado; não é calendário de venue) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/concerto.xml |
| Teatro Bradesco | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/teatro-bradesco.xml |
| Vibra São Paulo | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/vibra-sp.xml |
| Theatro Municipal | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/theatro-municipal.xml |
| Multi Arena Campinas | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/multi-arena-campinas.xml |
| Suhai Music Hall | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/suhai-music-hall.xml |
| Blue Note SP | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/blue-note-sp.xml |
| Arena B3 | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/arena-b3.xml |
| Bourbon Street | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/bourbon-street.xml |
| Mercado Livre Arena Pacaembu (Songkick) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/songkick-pacaembu.xml |
| Fabrique Club (Bandsintown) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/fabrique-club.xml |
| Estádio Morumbis (Live Nation) | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/morumbis-live-nation.xml |
| Carioca Club | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/carioca-club.xml |
| Juventus — Eventos | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/juventus-eventos.xml |
| Komplexo Tempo | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/komplexo-tempo.xml |
| BTG Pactual Hall | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/btg-pactual-hall.xml |
| Sala São Paulo | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/sala-sao-paulo.xml |
| Audio SP | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/audio-sp.xml |
| Teatro das Artes SP | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/teatro-das-artes-sp.xml |
| Casa de Francisca | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/casa-de-francisca.xml |
| Jazz B | https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/jazz-b.xml |

## Não foi possível

Venues sem fonte pública estável o bastante para um feed confiável (documentado a partir do probe):

- **PORTA (Shotgun)** — Shotgun; sem listagem scrapeável estável
- **The Cavern Club SP** — Sem feed/listagem pública útil
- **Multiplan Hall SC (Ticketmaster)** — Ticketmaster; bloqueios/JS
- **Manifesto Bar** — Sem fonte pública estável
- **Rockambole (Meaple)** — Meaple; sem scrape estável
- **Bona Casa de Música (Eventim)** — Eventim; sem listagem estável
- **Cultura Artística** — Sem fonte pública scrapeável
- **Cine Joia** — Sem listagem pública estável
- **Itaú Cultural (Inti)** — Inti; sem scrape estável

## CDN (jsDelivr)

Além do raw do GitHub, os XML em `feeds/` também podem ser servidos via jsDelivr, por exemplo:

`https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/page9-artes.xml`

(substitua o nome do arquivo conforme a tabela acima).

## Atualização

O workflow `.github/workflows/update-feeds.yml` roda `python3 build_all.py` e faz commit se houver mudança.

- Agenda: a cada 6 horas
- Manual: Actions → **Update RSS feeds** → **Run workflow**
