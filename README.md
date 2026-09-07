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
- Noize: https://feeds.feedburner.com/noize
- Ugly Things: https://ugly-things.com/feed/
- Panenka: https://www.panenka.org/feed/
- Treblezine: https://www.treblezine.com/feed/
- good-music.kiev.ua (junto): https://www.rssrssrssrss.com/api/merge?url=http%3A%2F%2Fgood-music.kiev.ua%2Fnews%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fload%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fpubl%2Frss%2F


## Nativos deste lote

Sites com RSS nativo usable — **não** são scrapados neste repo; use direto:

- **TIME** (todas as seções num feed): https://time.com/feed/
- **NOIZE**: https://feeds.feedburner.com/noize
- **ISMO** (Ghost principal cobre as seções): https://www.ismo.mov/rss/

## CDN (jsDelivr)

Além do raw do GitHub, os XML em `feeds/` também podem ser servidos via jsDelivr, por exemplo:

`https://cdn.jsdelivr.net/gh/pedrolemosfc/rss-feeds@main/feeds/page9-artes.xml`

(substitua o nome do arquivo conforme a tabela acima).

## Atualização

O workflow `.github/workflows/update-feeds.yml` roda `python3 build_all.py` e faz commit se houver mudança.

- Agenda: a cada 6 horas
- Manual: Actions → **Update RSS feeds** → **Run workflow**
