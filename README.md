# Media Renamed

Renomeador de séries e filmes com títulos obtidos do TMDB.  
Interface gráfica em GTK4 + Libadwaita.

## Dependências do sistema

- Python 3.11+
- GTK4 e Libadwaita (`libadwaita-1`)
- `python-gi` (PyGObject)

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
# edite .env e adicione seu TMDB_TOKEN
```

Obtenha um token em: https://www.themoviedb.org/settings/api

## Uso

```bash
PYTHONPATH=src python -m media_renamed.main
```

## Testes

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

## Launcher (.desktop)

Edite `launcher/media-renamed.desktop` substituindo `/CAMINHO/PARA/`  
pelo caminho absoluto do repositório, depois copie para:

```bash
cp launcher/media-renamed.desktop ~/.local/share/applications/
```

## Estrutura

```
src/media_renamed/
  api/    — cliente TMDB
  core/   — parser, scanner, renamer, models
  gui/    — interface GTK4
```
