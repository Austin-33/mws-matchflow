# AUSTIN LEAGUE CORE ⚡
**League Core Engine** — Sistema completo de gestão de campeonatos de futebol.

## Instalação

```bash
cd mws_matchflow
pip install -r requirements.txt
python init_db.py
python app.py
```

Abre o browser em: **http://localhost:5000**

## Funcionalidades

- 🔐 **Autenticação** — Login/Registo com perfis Admin e Manager
- 🏆 **Campeonatos** — Liga, Grupos+Mata-mata, Eliminatória direta
- ⚡ **Calendário Automático** — Round-robin, grupos e fases eliminatórias gerados automaticamente
- 🧑‍🤝‍🧑 **Sala da Equipa** — Plantel, formação, tática, capitão
- 📅 **Jogos do Dia** — Filtro por data e estado
- 📊 **Tabela Classificativa** — Atualizada automaticamente após cada resultado
- 🏅 **Ranking de Jogadores** — Golos, assistências, cartões, jogos disputados

## Estrutura

```
mws_matchflow/
├── app.py              # App factory + rota principal
├── extensions.py       # db e login_manager (evita circular imports)
├── init_db.py          # Script de inicialização da BD
├── models/
│   ├── user.py         # User (auth)
│   ├── team.py         # Team + Player
│   ├── tournament.py   # Tournament + Group + TournamentTeam
│   └── match.py        # Match + PlayerMatchStat
├── routes/
│   ├── auth.py         # Login/Registo/Logout
│   ├── tournament.py   # CRUD torneios + geração automática
│   ├── team.py         # CRUD equipas + jogadores
│   ├── match.py        # Resultados + estatísticas
│   └── player.py       # Ranking global
├── utils/
│   └── scheduler.py    # Algoritmos de calendário
├── templates/          # Jinja2 HTML (tema dark neon)
└── static/
    ├── css/style.css   # UI MWS dark theme
    └── js/main.js
```
