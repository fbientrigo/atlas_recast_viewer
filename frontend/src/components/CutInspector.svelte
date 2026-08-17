<script lang="ts">
  import type { CutDefinition } from '../data/schema';
  import { categoryLabel, cutText, kindLabel, t, type Language } from '../i18n';
  import MathExpression from './MathExpression.svelte';
  export let cut: CutDefinition;
  export let language: Language;
  $: copy = cutText(cut, language);
</script>

<article class="inspector" aria-live="polite">
  <div class="inspector-heading">
    <div>
      <p class="eyebrow">{t(language, 'stage')} {cut.order} · {categoryLabel(cut.category, language)}</p>
      <h3>{copy.name}</h3>
    </div>
    <span class:response={cut.kind === 'response_weight'} class="kind">{kindLabel(cut.kind, language)}</span>
  </div>

  <section class="equation-block">
    <h4>{t(language, 'technicalDefinition')}</h4>
    <MathExpression latex={cut.mathematical_latex} fallback={cut.mathematical_definition} />
  </section>
  <div class="explanation-grid">
    <section><h4>{t(language, 'physicalIntuition')}</h4><p>{copy.physical_meaning}</p></section>
    <section><h4>{t(language, 'whyUsed')}</h4><p>{copy.analysis_rationale}</p></section>
  </div>
  <details class="implementation-detail">
    <summary>{t(language, 'implementation')}</summary>
    <p><strong>{t(language, 'requiredFields')}:</strong> {cut.requires_fields.join(', ')}</p>
    <p><strong>{t(language, 'sourceCode')}:</strong> <code>{cut.source_line_or_symbol}</code></p>
  </details>
</article>
