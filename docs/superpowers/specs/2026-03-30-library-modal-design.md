# Modal de Visualização da Biblioteca

Modal para visualizar itens da biblioteca ao clicar neles na sidebar.

## Contexto

A sidebar "Biblioteca" na tela de tópicos lista itens multimídia (vídeos, PDFs, documentos). Atualmente clicar neles não faz nada. Este modal permite visualizar o conteúdo inline.

## Decisões de Design

| Decisão | Escolha |
|---------|---------|
| Abordagem | Alpine.js puro (dados já estão no template) |
| Vídeo YouTube | iframe embed 16:9 |
| PDF/document/other | Mensagem "Em breve" com ícone |
| Ao fechar | Destrói iframe (limpa src) para parar reprodução |

## Estrutura do Modal

### Abertura

Clicar na área do item (thumbnail/ícone ou nome) dispara:
```
$dispatch('open-library-modal', { type: '...', url: '...', name: '...' })
```

Os dados `type`, `url` e `name` já estão disponíveis no loop `{% for item in library_items %}`.

### Layout

Modal segue o padrão visual existente:
- Backdrop com blur + transições
- Painel `max-w-3xl`, `rounded-2xl`
- Botão X (usando macro `btn_icon`) no canto superior direito
- Escape para fechar

### Conteúdo por tipo

**Vídeo (`type == 'video'` com URL YouTube):**
- Título do item no topo
- iframe YouTube embed com `aspect-video` (16:9), autoplay desligado
- O YouTube ID é extraído da URL usando a regex `YOUTUBE_RE` que já existe no backend — no template, o `thumbnail_url` já contém o ID, mas para o embed precisamos extrair do `url` do item. Faremos isso com uma função Alpine simples.

**Outros tipos (`pdf`, `document`, `other`) ou vídeo sem URL:**
- Ícone do tipo (mesmo usado nos cards da biblioteca) centralizado
- Nome do item
- Texto "Em breve" em cinza

### Ao fechar

Quando o modal fecha, o Alpine limpa a variável `url` para que o iframe seja destruído e o vídeo pare de tocar.

## Integração com Templates

### topics.html

1. Cada item da biblioteca ganha um `@click` que dispara o evento (na div do thumbnail e no nome).
2. O modal fica no final do template, antes do fechamento do `{% block content %}`.
3. O modal usa `x-data` com estado: `show`, `type`, `url`, `name`.
4. Função Alpine `youtubeId(url)` extrai o ID do vídeo para montar a URL do embed.

## Fora de Escopo

- Upload de PDFs/documentos
- Visualizador de PDF inline
- Player de vídeo customizado (usa iframe YouTube nativo)
- Controles de legenda (campo `subtitle_path` existe mas não será usado)
