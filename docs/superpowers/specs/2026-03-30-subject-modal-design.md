# Modal de Assunto (Criar / Editar)

Modal unificado que serve tanto para criar um novo assunto quanto para editar um existente.

## Contexto

Atualmente os cards de assuntos na home possuem um menu dropdown com opções "Renomear", "Trocar imagem" e "Excluir", mas nenhuma está funcional. Também existe um botão "Novo Assunto" sem ação. Este modal substitui todas essas interações com um formulário único.

## Decisões de Design

| Decisão | Escolha |
|---------|---------|
| Abordagem | Alpine.js (estado local) + HTMX (requests ao servidor) |
| Slug do nome curto | Auto-gerado das 3 primeiras palavras do título, editável |
| Visibilidade padrão | Privado |
| Upload de imagem | Arquivo local; sem imagem usa gradiente como fallback |
| Exclusão | Só no modo edição, com confirmação por digitação do nome curto |

## Estrutura do Modal

### Abertura

- **Novo assunto:** botão "Novo Assunto" na home dispara `$dispatch('open-subject-modal')` sem dados. Alpine inicializa o form vazio.
- **Editar assunto:** item do menu dropdown no card dispara `$dispatch('open-subject-modal', { id, name, shortname, image_path, is_public })`. Alpine preenche o form com os dados existentes.

O modal usa `x-data` com um objeto de estado que diferencia os modos pela presença ou ausência de `id`.

### Layout do Form

O modal segue o estilo visual já existente no projeto (ver modal de detalhes em `topics.html`): backdrop com blur, painel centralizado com `rounded-2xl`, botão X no canto superior direito.

Conteúdo do form de cima para baixo:

1. **Imagem (16:9)** — Área com `aspect-ratio: 16/9` e `rounded-xl`.
   - Sem imagem: exibe gradiente colorido (mesmo padrão dos cards) com ícone centralizado.
   - Com imagem: exibe a imagem atual com `object-cover`.
   - Botão "Carregar imagem" / "Trocar imagem" sobreposto no canto inferior direito (fundo semi-transparente com backdrop-blur).
   - Input file hidden, acionado pelo botão. Aceita apenas imagens (`accept="image/*"`).
   - Ao selecionar, preview é exibido imediatamente via `URL.createObjectURL()`.

2. **Título** — Input text. Label "TÍTULO".
   - Placeholder: "Nome do assunto..."
   - Ao digitar, o nome curto é recalculado automaticamente (se o usuário não o tiver editado manualmente).

3. **Nome curto** — Input text. Label "NOME CURTO (usado na URL)".
   - Auto-gerado: pega as 3 primeiras palavras do título, converte para lowercase, remove acentos, substitui espaços por `-`, remove caracteres inválidos.
   - Campo editável — se o usuário alterar manualmente, o auto-geração para (flag `shortname_dirty`).
   - Dica abaixo do campo: "exemplo: /usuario/**nome-curto**"
   - Validação: mínimo 2 caracteres, apenas `a-z`, `0-9`, `-`.

4. **Visibilidade** — Toggle switch com descrição dinâmica.
   - OFF (padrão): "Privado — só você pode ver"
   - ON: "Público — qualquer pessoa pode ver"
   - Background do container muda: cinza (privado) → teal claro (público).

5. **Botões de ação** — Alinhados à direita.
   - "Cancelar" (botão outline) — fecha o modal.
   - "Criar Assunto" (modo criação) ou "Salvar" (modo edição) — botão teal sólido.

6. **Zona de perigo** (apenas modo edição) — Separada por borda vermelha no topo.
   - Título: "Zona de perigo"
   - Texto: "Para excluir, digite **{nome-curto}** abaixo:"
   - Input de confirmação + botão "Excluir".
   - Botão fica desabilitado (opacity 0.5) até o texto digitado coincidir exatamente com o nome curto do assunto.

## Rotas Backend (novas)

### POST /htmx/subjects

Cria um novo assunto. Recebe `multipart/form-data`:
- `name` (string, obrigatório)
- `shortname` (string, obrigatório, validado contra regex `^[a-z0-9-]{2,}$`)
- `is_public` (boolean, default false)
- `image` (file, opcional)

**Fluxo:**
1. Valida campos obrigatórios e formato do nome curto.
2. Verifica unicidade do `shortname` para o `owner_id`.
3. Se houver imagem, salva em `midias/` com nome único (uuid + extensão original).
4. Insere no banco.
5. **Sucesso:** retorna header `HX-Redirect` para `/{username}` (recarrega a home).
6. **Erro de nome curto duplicado:** retorna HTML do form com mensagem de erro inline no campo nome curto ("Este nome curto já está em uso. Escolha outro.") e status 422.

### PUT /htmx/subjects/{id}

Atualiza um assunto existente. Mesmos campos que o POST. Verifica que o assunto pertence ao usuário autenticado. Mesma lógica de validação e unicidade (excluindo o próprio registro).

**Sucesso:** retorna header `HX-Redirect` para `/{username}`.
**Erro:** retorna form com erro inline, status 422.

### DELETE /htmx/subjects/{id}

Exclui um assunto. Recebe `shortname_confirm` no body para validação.

**Fluxo:**
1. Verifica que o assunto pertence ao usuário autenticado.
2. Verifica que `shortname_confirm` coincide com o `shortname` real.
3. Remove o arquivo de imagem de `midias/` se existir.
4. Deleta o registro (cascade remove `subject_images` e `library_items`).
5. Retorna header `HX-Redirect` para `/{username}`.

### POST /htmx/subjects/{id}/image

Upload de imagem avulso (para preview imediato no modal sem salvar o form todo). Opcional — pode ser implementado depois se necessário.

## Integração com Templates

### home.html

- O modal fica no final do template (como o modal de detalhes em `topics.html`).
- O botão "Novo Assunto" ganha `@click="$dispatch('open-subject-modal')"`.
- Os itens do menu dropdown dos cards são atualizados:
  - "Renomear" e "Trocar imagem" são substituídos por "Editar" que dispara `$dispatch('open-subject-modal', { subject data })`.
  - "Excluir" é removido do dropdown (agora fica dentro do modal de edição).

### Partial (opcional)

Se o form ficar muito grande, pode ser extraído para `app/templates/partials/subject_modal.html` e incluído via `{% include %}`. Decisão de implementação.

## Geração do Nome Curto (algoritmo)

```
input:  "Programação em Python Avançado"
step 1: split em palavras → ["Programação", "em", "Python", "Avançado"]
step 2: pega as 3 primeiras → ["Programação", "em", "Python"]
step 3: join com espaço → "Programação em Python"
step 4: lowercase → "programação em python"
step 5: remove acentos (normalize NFD + strip diacritics) → "programacao em python"
step 6: substitui espaços e caracteres inválidos por "-" → "programacao-em-python"
step 7: remove "-" duplicados e das pontas → "programacao-em-python"
```

Implementado como função Alpine inline ou helper JS simples.

## Validação

| Campo | Regras | Mensagem de erro |
|-------|--------|-----------------|
| Título | Obrigatório, max 100 chars | "Informe o título do assunto" |
| Nome curto | Obrigatório, min 2 chars, regex `^[a-z0-9-]+$`, único por usuário | "Mínimo 2 caracteres" / "Apenas letras, números e hífens" / "Este nome curto já está em uso" |
| Imagem | Opcional, max 5MB, tipos image/* | "Arquivo muito grande (máx. 5MB)" / "Tipo de arquivo não suportado" |

Validação client-side (Alpine) para feedback imediato. Validação server-side como fonte de verdade.

## Comportamento de Erro

Quando o servidor retorna 422 (nome curto duplicado):
1. A rota retorna um response com header `HX-Trigger` contendo um evento custom (ex: `subject-error`) com a mensagem de erro em JSON.
2. O Alpine escuta esse evento e exibe a mensagem de erro inline abaixo do campo nome curto.
3. O foco vai para o campo nome curto via `$nextTick(() => $refs.shortname.focus())`.
4. O usuário corrige e submete novamente.

Isso mantém o form inteiramente no Alpine (sem re-render server-side do modal).

## Fora de Escopo

- Crop/redimensionamento de imagem no client
- Drag-and-drop para upload
- Reordenação de assuntos
- Upload de múltiplas imagens (tabela `subject_images` existe mas não será usada agora)
