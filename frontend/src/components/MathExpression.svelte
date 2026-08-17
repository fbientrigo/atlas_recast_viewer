<script lang="ts">
  import katex from 'katex';
  import 'katex/dist/katex.min.css';

  export let latex: string | undefined;
  export let fallback: string;

  $: rendered = latex
    ? katex.renderToString(latex, { displayMode: true, throwOnError: false, strict: 'warn', trust: false })
    : null;
</script>

{#if rendered}
  <div class="math-expression" aria-label={fallback}>{@html rendered}</div>
{:else}
  <p class="math-fallback">{fallback}</p>
{/if}
