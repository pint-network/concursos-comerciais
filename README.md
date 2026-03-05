# Pint.Network — Análise de Concursos Comerciais

Dashboard interativo comparando os vencedores dos dois principais concursos comerciais de cerveja do Brasil, por estilo.

**Site:** https://pint-network.github.io/concursos-comerciais/

---

## Concursos

| Concurso | Edição |
|---|---|
| CBC — Concurso Brasileiro de Cervejas | 2026 |
| Concurso Brasileiro de Cervejas de Blumenau | 2026 |

## Funcionalidades

- Listagem de todos os estilos com medalhas em ambos os concursos
- Comparação lado a lado dos vencedores (Ouro, Prata, Bronze) por estilo
- Destaque de estilos e cervejarias premiados em ambos os concursos
- Busca e filtros por concurso e por coincidências
- Página de cervejarias: quem ganhou em ambos, somente no CBC ou somente em Blumenau
- Clique em qualquer cervejaria para ver todos os seus prêmios
- Filtro por ano (preparado para edições futuras)

## Dados

| Arquivo | Descrição |
|---|---|
| `results.json` | Dados consolidados de ambos os concursos |
| `cbc-2026-results.csv` | Resultados do CBC 2026 |
| `concurso-brasileiro-de-cervejas-results.csv` | Resultados do Concurso de Blumenau 2026 |

Os dados foram extraídos dos PDFs oficiais de resultados usando `pdfplumber` (Blumenau) e `PyPDF2` (CBC), normalizados e combinados em um único JSON embarcado no dashboard.

## Estrutura do JSON

```json
{
  "styles": ["Adambier", "Aged Beer", "..."],
  "data": {
    "Adambier": {
      "cbc2026": [
        { "medal": "Ouro", "beer": "Nome da Cerveja", "brewery": "Cervejaria", "state": "SC" }
      ],
      "cbc": []
    }
  }
}
```

## Desenvolvimento local

Abra `index.html` diretamente no navegador — não requer servidor.

Para regenerar o dashboard a partir dos CSVs:

```bash
python3 normalize.py       # normaliza os CSVs
python3 build_dashboard.py # gera o index.html
```
