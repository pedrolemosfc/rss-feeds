# RSS feeds

Feeds scrapados e atualizados automaticamente via **GitHub Actions** (a cada 6 horas), sem depender de bots externos.

## Feeds scrapados (cole no leitor)

| Fonte | Feed |
|------|------|
| Folha — Jazz + Críticas + Show (junto) | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/folha-musica-topicos.xml |
| Guia Folha — Restaurantes + Shows (junto) | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/guia-folha-restaurantes-shows.xml |
| Estadão — Sérgio Martins | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/estadao-sergio-martins.xml |
| Veja SP — Tudo de Som | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/vejasp-tudo-de-som.xml |
| Correio Braziliense — Irlam Rocha Lima | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/correio-irlam-rocha-lima.xml |
| Billboard Brasil — Sérgio Martins | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/billboard-br-sergio-martins.xml |
| ASIL Insights | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/asil-insights.xml |
| xAI News | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/xai-news.xml |
| Claude Blog | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/claude-blog.xml |

### Também disponíveis (seções individuais)

| Fonte | Feed |
|------|------|
| Folha Jazz | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/folha-jazz.xml |
| Folha Críticas de música | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/folha-criticas-de-musica.xml |
| Folha Show | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/folha-show.xml |
| Guia Restaurantes | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/guia-restaurantes.xml |
| Guia Shows | https://raw.githubusercontent.com/pedrolemosfc/rss-feeds/main/feeds/guia-shows.xml |

## Feeds nativos (não passam por este repo)

- Piauí: https://piaui.uol.com.br/feed/
- Noize: https://feeds.feedburner.com/noize
- Ugly Things: https://ugly-things.com/feed/
- Panenka: https://www.panenka.org/feed/
- Treblezine: https://www.treblezine.com/feed/
- good-music.kiev.ua (junto): https://www.rssrssrssrss.com/api/merge?url=http%3A%2F%2Fgood-music.kiev.ua%2Fnews%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fload%2Frss%2F&url=http%3A%2F%2Fgood-music.kiev.ua%2Fpubl%2Frss%2F

## Atualização

O workflow `.github/workflows/update-feeds.yml` roda `python3 build_all.py` e faz commit se houver mudança.

- Agenda: a cada 6 horas
- Manual: Actions → **Update RSS feeds** → **Run workflow**
