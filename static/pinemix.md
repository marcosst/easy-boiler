---
inclusion: manual
---

# Pinemix — Componentes Disponíveis

Biblioteca de componentes Alpine.js v3 + Tailwind CSS v4, gratuitos e prontos para copy-paste.
Site: https://pinemix.com/components

Ao criar UI no projeto, consulte esta lista e use o componente mais adequado.
Cada componente tem sua página com o código completo em: `https://pinemix.com/components/<slug>`

## Lista de Componentes (27)

| Componente | Slug | Descrição | Quando usar |
|---|---|---|---|
| Accordion | `accordion` | Alterna conteúdo exclusivamente | FAQs, seções colapsáveis |
| Banner | `banner` | Mensagens ou alertas configuráveis | Avisos, notificações de topo de página |
| Color Picker | `color-picker` | Seleção de cor via paleta ou input | Formulários com escolha de cor |
| Command Palette | `command-palette` | Acesso rápido a comandos e ações | Busca global, atalhos de teclado |
| Copy to Clipboard | `copy-to-clipboard` | Copia texto para a área de transferência | Exibir códigos, tokens, links |
| Countdown | `countdown` | Timer de contagem regressiva customizável | Eventos, prazos, promoções |
| Dark Mode Toggle | `dark-mode-toggle` | Alterna entre modo claro e escuro | Preferência de tema do usuário |
| Dropdown | `dropdown` | Menu customizável com lista de opções | Menus de ação, seleção de opções |
| Image Gallery | `image-gallery` | Galeria em grid com lightbox fullscreen | Exibição de imagens com zoom |
| Image Slider | `image-slider` | Sequência de imagens com navegação e autoplay | Carrosséis, banners de imagem |
| Marquee | `marquee` | Animação de scroll infinito para qualquer conteúdo | Logos, destaques, feeds |
| Modal | `modal` | Conteúdo sobreposto à página atual | Confirmações, formulários, detalhes |
| Notification | `notification` | Elemento empilhável de informação em overlay | Toasts, alertas de feedback |
| Offcanvas | `offcanvas` | Sidebar oculta que desliza pela borda da tela | Menu mobile, filtros laterais |
| Popover | `popover` | Janela overlay pequena sobre o conteúdo | Dicas, detalhes extras, mini-menus |
| Password Strength | `password-strength` | Exibe a força de uma senha | Formulários de cadastro/senha |
| Pricing Switch | `pricing-switch` | Toggle entre preço mensal e anual | Páginas de planos e preços |
| Progress Bar | `progress-bar` | Indicador visual de progresso de tarefa | Upload, steps, carregamento |
| Rating | `rating` | Avaliação com estrelas | Reviews, feedback de produtos |
| Select Menu | `select-menu` | Seleção visual e flexível de opções | Substituto para `<select>` nativo |
| Side Navigation | `side-navigation` | Menu de navegação lateral | Dashboards, painéis admin |
| Skeleton Loader | `skeleton-loader` | Esqueleto de carregamento enquanto conteúdo carrega | Loading states de listas e cards |
| Table Sorting | `table-sorting` | Ordenação de tabela por clique no cabeçalho | Tabelas de dados |
| Tag Input | `tag-input` | Input que converte valores digitados em tags removíveis | Campos de tags, categorias, filtros |
| Tabs | `tabs` | Navegação entre seções na mesma página | Conteúdo em abas |
| Tooltip | `tooltip` | Elemento pequeno com informação adicional | Ícones com descrição, hints |
| Two Factor | `two-factor` | Formulário de autenticação com código de 6 dígitos | Telas de 2FA / MFA |

## Como usar

1. Acesse a página do componente: `https://pinemix.com/components/<slug>`
2. Copie o código HTML do componente
3. Cole no template Jinja2 correspondente
4. Alpine.js e Tailwind já estão carregados no `base.html` via CDN

## Dependências já incluídas no projeto

```html
<script src="https://cdn.tailwindcss.com?plugins=forms"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

> Alguns componentes requerem plugins extras do Alpine.js (ex: Focus Plugin para o Command Palette).
> Verifique na página do componente se há dependências adicionais.
